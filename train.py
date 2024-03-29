import numpy as np
import torch
import yaml
from torch.utils.benchmark import timer
from torch.utils.data import DataLoader

from src.data_processing import DataProcessor, pairwise_sentence_iterator
from src.device import DEVICE
from src.evaluate import evaluate_model
from src.model import Sequence2SequenceTransformer, training_epoch
from src.predict import translate

torch.manual_seed(0)

# Open our general config file.
with open('config.yml', 'r') as configfile:
    config = yaml.load(configfile, Loader=yaml.SafeLoader)

# Instantiate a DataProcessor object for the languages we have specified.
data_processor = DataProcessor(
    language_a=config['language_a'],
    language_b=config['language_b'],
    train_file_language_a=config['language_a_train_file'],
    train_file_language_b=config['language_b_train_file']
)

# Prepare the training dataset iterator
train_iter = pairwise_sentence_iterator(
    target_file_language_a=config['language_a_train_file'],
    target_file_language_b=config['language_b_train_file']
)

# Prepare the testing dataset iterator
test_iter = pairwise_sentence_iterator(
    target_file_language_a=config['language_a_test_file'],
    target_file_language_b=config['language_b_test_file']
)

# Create a training data DataLoader to be used for the training loop
train_dataloader = DataLoader(
    list(train_iter),
    batch_size=config['training']['batch_size'],
    shuffle=True,
    collate_fn=data_processor.collation
)

# Create a test data DataLoader to be used for evaluation
test_dataloader = DataLoader(
    list(test_iter),
    batch_size=config['training']['batch_size'],
    shuffle=True,
    collate_fn=data_processor.collation
)

transformer = Sequence2SequenceTransformer(num_encoder_layers=config['model']['num_encoder_layers'],
                                           num_decoder_layers=config['model']['num_decoder_layers'],
                                           d_model=config['model']['embedding_size'],
                                           nhead=config['model']['num_heads'],
                                           src_vocab_size=len(data_processor.vocab_a),
                                           tgt_vocab_size=len(data_processor.vocab_b),
                                           dim_feedforward=config['model']['feed_forward_hidden_dimensions'],
                                           dropout=config['model']['dropout_rate'])
transformer = transformer.to(DEVICE)

for p in transformer.parameters():
    if p.dim() > 1:
        torch.nn.init.xavier_uniform_(p)

optimiser = torch.optim.Adam(transformer.parameters(), lr=0.0001,
                             betas=(0.9, 0.98), eps=1e-9)
loss_func = torch.nn.CrossEntropyLoss(ignore_index=data_processor.pad_id)

print(f"Running train...")
for epoch in range(1, config['training']['num_epochs'] + 1):
    start_time = timer()

    train_loss = training_epoch(transformer,
                                train_dataloader,
                                create_mask=data_processor.create_mask,
                                optimiser=optimiser,
                                loss_func=loss_func)
    val_loss = evaluate_model(transformer,
                              val_dataloader=test_dataloader,
                              loss_fn=loss_func,
                              create_mask=data_processor.create_mask)
    end_time = timer()
    print(f"Epoch: {epoch},"
          f" Train loss: {np.average(train_loss):.3f},"
          f" Val loss: {np.average(val_loss):.3f},"
          f" "f"Epoch time = {(end_time - start_time)}s")


# Example usage of the resultant model:

print(translate(model=transformer, data_processor=data_processor, src_sentence="Get up."))