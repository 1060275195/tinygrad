#!/usr/bin/env python3
import numpy as np
import random
from tinygrad.tensor import Tensor

from extra.utils import get_parameters
from extra.training import train, evaluate
from tinygrad.optim import Adam

# dataset idea from https://github.com/karpathy/minGPT/blob/master/play_math.ipynb
def make_dataset():
  ds = []
  for i in range(100):
    for j in range(100):
      s = i+j
      ds.append([i//10, i%10, j//10, j%10, s//100, (s//10)%10, s%10])
  random.shuffle(ds)
  ds = np.array(ds)
  ds_X = ds[:, 0:6]
  ds_Y = np.copy(ds[:, 1:])
  ds_X_train, ds_X_test = ds_X[0:8000], ds_X[8000:]
  ds_Y_train, ds_Y_test = ds_Y[0:8000], ds_Y[8000:]

  return ds_X_train, ds_Y_train, ds_X_test, ds_Y_test

class TransformerBlock:
  def __init__(self, embed_dim, num_heads):
    # Multi-Head Attention
    self.num_heads = num_heads
    self.head_size = embed_dim // num_heads
    assert self.head_size * self.num_heads == embed_dim

    # looks like bias is useless
    self.query_dense = Tensor.uniform(embed_dim, embed_dim)
    self.key_dense = Tensor.uniform(embed_dim, embed_dim)
    self.value_dense = Tensor.uniform(embed_dim, embed_dim)

    self.final = Tensor.uniform(embed_dim, embed_dim)

    self.ff1 = Tensor.uniform(embed_dim, embed_dim)
    self.ff2 = Tensor.uniform(embed_dim, embed_dim)

  def __call__(self, x):
    # bs x T x embed_dim
    bs = x.shape[0]
    inputs = x.reshape(shape=(-1, self.num_heads * self.head_size))

    # run multi head attention (bs, T, num_heads, head_size)
    query, key, value = [inputs.dot(y) \
      .reshape(shape=(bs, -1, self.num_heads, self.head_size)) \
      for y in [self.query_dense, self.key_dense, self.value_dense]]

    query = query.transpose(order=(0,2,1,3))  # (bs, num_heads, T, head_size)
    key = key.transpose(order=(0,2,3,1))      # (bs, num_heads, head_size, T)
    value = value.transpose(order=(0,2,1,3))  # (bs, num_heads, T, head_size)

    score = query.dot(key) * (1 / np.sqrt(self.head_size))
    # TODO: this should be a normal softmax
    weights = score.logsoftmax()              # (bs, num_heads, T, T)
    attention = weights.dot(value).transpose(order=(0,2,1,3))
    x = inputs + attention.reshape(shape=(-1, self.num_heads * self.head_size)).dot(self.final)
    # layernorm
    x = x + x.dot(self.ff1).relu().dot(self.ff2)
    # layernorm
    return x.reshape(shape=(bs, -1, self.num_heads * self.head_size))

class Transformer:
  def __init__(self, syms, maxlen, cnt, embed_dim, num_heads):
    self.maxlen, self.syms = maxlen, syms
    self.embed = Tensor.uniform(maxlen+syms, embed_dim)
    self.tbs = []
    for i in range(cnt):
      self.tbs.append(TransformerBlock(embed_dim, num_heads))
    self.final = Tensor.uniform(embed_dim, syms)

  def forward(self, x):
    bs = x.shape[0]
    xnp = x.cpu().data
    onehot = np.zeros((bs, x.shape[1], self.maxlen+self.syms), dtype=np.float32)
    for i in range(x.shape[1]):
      onehot[range(bs), i, i] = 1
      onehot[range(bs), i, self.maxlen + xnp[:, i]] = 1
    onehot = onehot.reshape(bs*x.shape[1], self.maxlen+self.syms)

    x = Tensor(onehot, device=x.device).dot(self.embed).reshape(shape=(bs, x.shape[1], -1))
    for t in self.tbs:
      x = t(x)
    x = x.reshape(shape=(-1, x.shape[-1])).dot(self.final).logsoftmax()
    return x.reshape(shape=(bs, -1, x.shape[-1]))
    
from tinygrad.optim import Adam
if __name__ == "__main__":
  model = Transformer(10, 6, 2, 128, 4)

  #in1 = Tensor.zeros(20, 6, 128)
  #ret = model.forward(in1)
  #print(ret.shape)

  X_train, Y_train, X_test, Y_test = make_dataset()
  optim = Adam(get_parameters(model), lr=0.001)
  train(model, X_train, Y_train, optim, 100)




