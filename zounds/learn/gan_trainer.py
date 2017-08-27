import numpy as np
import torch
from torch.autograd import Variable


class GanTrainer(object):
    def __init__(
            self,
            generator,
            discriminator,
            loss,
            generator_optim_func,
            discriminator_optim_func,
            latent_dimension):

        super(GanTrainer, self).__init__()
        self.discriminator_optim_func = discriminator_optim_func
        self.generator_optim_func = generator_optim_func
        self.latent_dimension = latent_dimension
        self.loss = loss
        self.discriminator = discriminator
        self.generator = generator

    def train(self, data, epochs, batch_size):

        data = data.astype(np.float32)

        zdim = self.latent_dimension

        # TODO: These dimensions work for vanilla GANs, but need to be
        # reversed (batch_size, zdim, 1) for convolutional GANs

        noise_shape = (batch_size,) + self.latent_dimension
        noise = torch.FloatTensor(*noise_shape)
        fixed_noise = torch.FloatTensor(*noise_shape).normal_(0, 1)
        label = torch.FloatTensor(batch_size)
        real_label = 1
        fake_label = 0

        self.generator.cuda()
        self.discriminator.cuda()
        self.loss.cuda()
        label = label.cuda()
        noise, fixed_noise = noise.cuda(), fixed_noise.cuda()

        generator_optim = self.generator_optim_func(
            self.generator.parameters())
        discriminator_optim = self.discriminator_optim_func(
            self.discriminator.parameters())

        for epoch in xrange(epochs):
            for i in xrange(0, len(data), batch_size):
                minibatch = data[i: i + batch_size]

                if len(minibatch) != batch_size:
                    continue

                inp = torch.from_numpy(minibatch)
                inp = inp.cuda()

                # train discriminator on real data with one-sided label
                # smoothing
                self.discriminator.zero_grad()
                soft_labels = \
                    0.7 + (np.random.random_sample(batch_size) * 0.4) \
                        .astype(np.float32)
                soft_labels = torch.from_numpy(soft_labels)
                label.copy_(soft_labels)

                input_v = Variable(inp)
                label_v = Variable(label)

                output = self.discriminator.forward(input_v)
                real_error = self.loss(output, label_v)
                real_error.backward()

                # train discriminator on fake data
                noise.normal_(0, 1)
                noise_v = Variable(noise)
                fake = self.generator.forward(noise_v)
                label.fill_(fake_label)
                label_v = Variable(label)
                output = self.discriminator.forward(fake.detach())
                fake_error = self.loss(output, label_v)
                fake_error.backward()
                discriminator_error = real_error + fake_error
                discriminator_optim.step()

                # train generator
                self.generator.zero_grad()
                label.fill_(real_label)
                label_v = Variable(label)
                output = self.discriminator.forward(fake)
                generator_error = self.loss(output, label_v)
                generator_error.backward()
                generator_optim.step()

                gl = generator_error.data[0]
                dl = discriminator_error.data[0]
                re = real_error.data[0]
                fe = fake_error.data[0]

                if i % 10 == 0:
                    print \
                        'Epoch {epoch}, batch {i}, generator {gl}, real_error {re}, fake_error {fe}' \
                            .format(**locals())

                    # fake_samples = fake.cpu().data.numpy().squeeze()
                    # np.save('fake.dat', fake_samples)

        return self.generator, self.discriminator
