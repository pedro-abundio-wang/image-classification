r"""Downloads and converts a particular dataset.

Usage:
```shell

$ python download_and_convert_data.py \
    --dataset_name=flowers \
    --dataset_dir=/tmp/flowers

$ python download_and_convert_data.py \
    --dataset_name=cifar10 \
    --dataset_dir=/tmp/cifar10

$ python download_and_convert_data.py \
    --dataset_name=mnist \
    --dataset_dir=/tmp/mnist

$ python download_and_convert_data.py \
    --dataset_name=visualwakewords \
    --dataset_dir=/tmp/visualwakewords

```
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags

from vision.image_classification.slim.datasets import download_and_convert_cifar10
from vision.image_classification.slim.datasets import download_and_convert_flowers
from vision.image_classification.slim.datasets import download_and_convert_mnist
from vision.image_classification.slim.datasets import download_and_convert_visualwakewords

flags.DEFINE_string(
    'dataset_name',
    None,
    'The name of the dataset to convert, one of "flowers", "cifar10", "mnist", "visualwakewords"'
    )

flags.DEFINE_string(
    'dataset_dir',
    None,
    'The directory where the output TFRecords and temporary files are saved.')

flags.DEFINE_float(
    'small_object_area_threshold', 0.005,
    'For --dataset_name=visualwakewords only. Threshold of fraction of image '
    'area below which small objects are filtered')

flags.DEFINE_string(
    'foreground_class_of_interest', 'person',
    'For --dataset_name=visualwakewords only. Build a binary classifier based '
    'on the presence or absence of this object in the image.')

FLAGS = flags.FLAGS


def main(_):
  if not FLAGS.dataset_name:
    raise ValueError('You must supply the dataset name with --dataset_name')
  if not FLAGS.dataset_dir:
    raise ValueError('You must supply the dataset directory with --dataset_dir')

  if FLAGS.dataset_name == 'flowers':
    download_and_convert_flowers.run(FLAGS.dataset_dir)
  elif FLAGS.dataset_name == 'cifar10':
    download_and_convert_cifar10.run(FLAGS.dataset_dir)
  elif FLAGS.dataset_name == 'mnist':
    download_and_convert_mnist.run(FLAGS.dataset_dir)
  elif FLAGS.dataset_name == 'visualwakewords':
    download_and_convert_visualwakewords.run(
        FLAGS.dataset_dir, FLAGS.small_object_area_threshold,
        FLAGS.foreground_class_of_interest)
  else:
    raise ValueError(
        'dataset_name [%s] was not recognized.' % FLAGS.dataset_name)

if __name__ == '__main__':
  app.run(main)
