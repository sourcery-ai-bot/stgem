#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

import torch
import torch.nn as nn

# For visualizing the computational graphs.
#from torchviz import make_dot

from neural_networks.generator import GeneratorNetwork
from neural_networks.discriminator import DiscriminatorNetwork
from neural_networks.validator import ValidatorNetwork

class Model:
  """
  Base class for all models.
  """

  def __init__(self, sut, validator, device):
    self.sut = sut
    self.device = device
    self.validator = validator

  def train_with_batch(self, dataX, dataY, epochs=1, validator_epochs=1, discriminator_epochs=1, use_final=-1):
    raise NotImplementedError()

  def generate_test(self, N=1):
    raise NotImplementedError()

  def validity(self, tests):
    """
    Validate the given test using the true validator.

    Args:
      tests (np.ndarray): Array of shape (N, self.sut.ndimensions).

    Returns:
      output (np.ndarray): Array of shape (N, 1).
    """

    if len(tests.shape) != 2 or tests.shape[1] != self.sut.ndimensions:
      raise ValueError("Input array expected to have shape (N, {}).".format(self.sut.ndimensions))

    if self.validator is None:
      result = np.ones(shape=(tests.shape[0], 1))
    else:
      result = self.validator.validity(tests)

    return result

  def predict_validity(self, tests):
    """
    Validate the given test using the learned proxy validator.

    Args:
      tests (np.ndarray): Array of N tests with shape (N, self.sut.ndimensions).

    Returns:
      result (np.ndarray): Array of shape (N, 1).
    """

    if len(tests.shape) != 2 or tests.shape[1] != self.sut.ndimensions:
      raise ValueError("Input array expected to have shape (N, {}).".format(self.sut.ndimensions))

    if self.validator is None:
      result = np.ones(shape=(tests.shape[0], 1))
    else:
      result = self.validator.predict_validity(tests)

    return result

class GAN(Model):
  """
  Implements the GAN model.
  """

  def __init__(self, sut, validator, device):
    # TODO: describe the arguments
    super().__init__(sut, validator, device)

    self.modelG = None
    self.modelD = None
    # Input dimension for the noise inputted to the generator.
    self.noise_dim = 100
    # Number of neurons per layer in the neural networks.
    self.neurons = 128

    # Initialize neural network models.
    self.modelG = GeneratorNetwork(input_shape=self.noise_dim, output_shape=self.sut.ndimensions, neurons=self.neurons).to(self.device)
    self.modelD = DiscriminatorNetwork(input_shape=self.sut.ndimensions, neurons=self.neurons).to(self.device)

    # Loss functions.
    # TODO: figure out a reasonable default and make configurable.
    self.lossG = nn.BCELoss() # binary cross entropy
    #self.lossD = nn.L1Loss()
    self.lossD = nn.MSELoss() # mean square error

    # Optimizers.
    # TODO: figure out reasonable defaults and make configurable.
    lr = 0.001
    #self.optimizerD = torch.optim.RMSprop(self.modelD.parameters(), lr=lr)
    #self.optimizerG = torch.optim.RMSprop(self.modelG.parameters(), lr=lr)
    self.optimizerD = torch.optim.Adam(self.modelD.parameters(), lr=lr)
    self.optimizerG = torch.optim.Adam(self.modelG.parameters(), lr=lr)

  def train_with_batch(self, dataX, dataY, epochs=1, generator_epochs=1, validator_epochs=1, discriminator_epochs=1, validator_data_size=1, discriminator_data_size=1, use_final=-1):
    """
    Train the GAN with a new batch of learning data.

    Args:
      dataX (np.ndarray):             Array of tests of shape
                                      (N, self.sut.ndimensions).
      dataY (np.ndarray):             Array of test outputs of shape (N, 1).
      epochs (int):                   Number of epochs (total training over the
                                      complete data).
      generator_epochs (int):         Number of epochs for the training of the
                                      generator with respect to the
                                      discriminator (this many rounds per
                                      epoch).
      validator_epochs (int):         Number of epochs for the training of the
                                      validator (this many rounds per
                                      epoch).
      discriminator_epochs (int):     Number of epochs for the training of the
                                      discriminator (this many rounds per
                                      epoch).
      validator_data_size (int):      Number of tests generated from noise
                                      during the training of the generator
                                      with respect to the validator.
      discriminator_data_size (int):  Number of tests generated from noise
                                      during the training of the generator
                                      with respect to the discriminator.
      use_final (int):                Use only this many training samples from
                                      the end. If < 0, then use all samples.
    """

    if len(dataX.shape) != 2 or dataX.shape[1] != self.sut.ndimensions:
      raise ValueError("Test array expected to have shape (N, {}).".format(self.ndimensions))
    if len(dataY.shape) != 2 or dataY.shape[0] < dataX.shape[0]:
      raise ValueError("Output array should have at least as many elements as there are tests.")
    if epochs <= 0:
      raise ValueError("The number of epochs should be positive.")
    if validator_data_size <= 0:
      raise ValueError("The validator data size should be positive.")
    if discriminator_data_size <= 0:
      raise ValueError("The validator data size should be positive.")
    if discriminator_epochs <= 0:
      raise ValueError("The number of discriminator epochs should be positive.")

    start = 0 if use_final < 0 else dataX.shape[0] - use_final
    dataX = torch.from_numpy(dataX[start:dataX.shape[0],:]).float().to(self.device)
    dataY = torch.from_numpy(dataY[start:dataY.shape[0],:]).float().to(self.device)

    # Disable training for validator.
    if self.validator is not None:
      self.validator.modelV.train(False)
    # Enable training for the generator and discriminator.
    self.modelG.train(True)
    self.modelD.train(True)

    for n in range(epochs):
      # Train the discriminator.
      # -----------------------------------------------------------------------
      # We want the discriminator to learn the mapping from tests to test
      # outputs.
      self.modelD.train(True)
      for m in range(discriminator_epochs):
        # We the values from [0, 1] to \R using a logit transformation so that
        # MSE loss works better. Since logit is undefined in 0 and 1, we
        # actually first transform the values to the interval [0.01, 0.99].
        D_loss = self.lossD(torch.logit(self.modelD(0.98*dataX + 0.01)), torch.logit(0.98*dataY + 0.01))
        self.optimizerD.zero_grad()
        D_loss.backward()
        self.optimizerD.step()

        print("Epoch {}/{}, Discriminator epoch {}/{}, Loss: {}".format(n + 1, epochs, m + 1, discriminator_epochs, D_loss))

      self.modelD.train(False)

      # Visualize the computational graph.
      #print(make_dot(D_loss, params=dict(self.modelD.named_parameters())))

      # Train the generator on the validator.
      # -----------------------------------------------------------------------
      # We generate noise and label it to have output 1 (valid). Training the
      # generator in this way should shift it to generate more valid tests.
      if self.validator is not None:
        noise = ((torch.rand(size=(validator_data_size, self.modelG.input_shape)) - 0.5)/0.5).to(self.device)
        fake_label = torch.ones(size=(validator_data_size, 1)).to(self.device)

        for k in range(validator_epochs):
          outputs = self.validator.modelV(self.modelG(noise))
          G_loss = self.lossG(outputs, fake_label)
          self.optimizerG.zero_grad()
          G_loss.backward()
          #print(self.modelG.glayer2.weight.grad)
          self.optimizerG.step()

          print("Epoch {}/{}, Validator epoch: {}/{}, Loss: {}".format(n + 1, epochs, k + 1, validator_epochs, G_loss))

      # Train the generator on the discriminator.
      # -----------------------------------------------------------------------
      # We generate noise and label it to have output 1 (high fitness).
      # Training the generator in this way should shift it to generate tests
      # with high output values (high fitness).
      if self.validator is not None:
        # We need to generate valid tests in order not to confuse the generator
        # by garbage inputs (invalid tests with high fitness do not exist).
        self.modelG.train(False)
        inputs = np.zeros(shape=(discriminator_data_size, self.sut.ndimensions))
        k = 0
        while k < discriminator_data_size:
          new_test = self.modelG(((torch.rand(size=(1, self.modelG.input_shape)) - 0.5)/0.5).to(self.device)).detach().numpy()
          if self.validator.validity(new_test)[0,0] == 0.0: continue
          inputs[k,:] = new_test[0,:]
          k += 1
          #print(k)

        self.modelG.train(True)
        inputs = torch.from_numpy(inputs).float.to(self.device)
      else:
        inputs = ((torch.rand(size=(discriminator_data_size, self.modelG.input_shape)) - 0.5)/0.5).to(self.device)

      fake_label = torch.ones(size=(discriminator_data_size, 1)).to(self.device)

      # Notice the following subtlety. Above the tensor 'outputs' contains
      # information on how it is computed (the computation graph is being kept
      # track off) up to the original input 'noise' which does not anymore
      # depend on previous operations. Since 'self.modelD' is used as part of
      # the computation, its parameters are present in the computation graph.
      # These parameters are however not updated because the optimizer is
      # initialized only for the parameters of 'self.modelG' (see the
      # initialization of 'self.modelG'.

      for k in range(generator_epochs):
        outputs = self.modelD(self.modelG(inputs))
        G_loss = self.lossG(outputs, fake_label)
        self.optimizerG.zero_grad()
        G_loss.backward()
        self.optimizerG.step()
        print("Epoch {}/{}, Generator epoch: {}/{}, Loss: {}".format(n + 1, epochs, k + 1, generator_epochs, G_loss))

      self.modelG.train(False)

      # Visualize the computational graph.
      #print(make_dot(G_loss, params=dict(self.modelG.named_parameters())))

  def generate_test(self, N=1):
    """
    Generate N random tests.

    Args:
      N (int): Number of tests to be generated.

    Returns:
      output (np.ndarray): Array of shape (N, self.sut.ndimensions).
    """

    if N <= 0:
      raise ValueError("The number of tests should be positive.")

    # Generate uniform noise in [-1, 1].
    noise = ((torch.rand(size=(N, self.noise_dim)) - 0.5)/0.5).to(self.device)
    return self.modelG(noise).cpu().detach().numpy()

  def predict_fitness(self, test):
    """
    Predicts the fitness of the given test.

    Args:
      test (np.ndarray): Array of shape (N, self.sut.ndimensions).

    Returns:
      output (np.ndarray): Array of shape (N, 1).
    """

    if len(test.shape) != 2 or test.shape[1] != self.sut.ndimensions:
      raise ValueError("Input array expected to have shape (N, {}).".format(self.sut.ndimensions))

    test_tensor = torch.from_numpy(test).float().to(self.device)
    return self.modelD(test_tensor).cpu().detach().numpy()

class RandomGenerator(Model):
  """
  Implements the random test generator.
  """

  def __init__(self, sut, validator, device):
    # TODO: describe the arguments
    super().__init__(sut, validator, device)

  def train_with_batch(self, dataX, dataY, epochs=1, validator_epochs=1, discriminator_epochs=1, use_final=-1):
    pass

  def generate_test(self, N=1):
    """
    Generate N random tests.

    Args:
      N (int): Number of tests to be generated.

    Returns:
      output (np.ndarray): Array of shape (N, self.sut.ndimensions).
    """

    if N <= 0:
      raise ValueError("The number of tests should be positive.")

    return np.random.uniform(-1, 1, (N, self.sut.ndimensions))

  def predict_fitness(self, test):
    """
    Predicts the fitness of the given test.

    Args:
      test (np.ndarray): Array of shape (N, self.sut.ndimensions).

    Returns:
      output (np.ndarray): Array of shape (N, 1).
    """

    if len(test.shape) != 2 or test.shape[1] != self.sut.ndimensions:
      raise ValueError("Input array expected to have shape (N, {}).".format(self.sut.ndimensions))

    return np.ones(shape=(test.shape[0], 1))

