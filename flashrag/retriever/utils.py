import faiss
import json
from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np
from sqlite_utils import Database
import torch.nn.functional as F

from transformers import AutoTokenizer, AutoModel


def load_model(
        model_path: str, 
        use_fp16: bool = False
    ):
    model = AutoModel.from_pretrained(model_path, trust_remote_code=True)
    model.eval()
    model.cuda()
    if use_fp16: 
        model = model.half()
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    return model, tokenizer


def pooling(
        pooler_output,
        last_hidden_state,
        attention_mask = None,
        pooling_method = "mean"
    ):
    if pooling_method == "mean":
        last_hidden = last_hidden_state.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]
    elif pooling_method == "cls":
        return last_hidden_state[:, 0]
    elif pooling_method == "pooler":
        return pooler_output
    else:
        raise NotImplementedError("Pooling method not implemented!")

def base_content_function(item):
    if 'title' in item:
        return "\"{}\"\n{}".format(item['title'], item['text'])
    else:
        return item['text']

def load_database(database_path: str):
    db = Database(database_path)
    corpus = db['docs']
    return corpus
    

def load_corpus(
        corpus_path: str,
        content_function: callable = lambda item: "\"{}\"\n{}".format(item['title'], item['text'])
    ):
    
    corpus = []
    with open(corpus_path, "r") as f:
        if ".jsonl" in corpus_path:
            for line in f:
                corpus.append(json.loads(line))
        else:
            corpus = json.load(f)
    
    if 'contents' not in corpus[0]:
        for item in corpus:
            item['contents'] = content_function(item)

    return corpus