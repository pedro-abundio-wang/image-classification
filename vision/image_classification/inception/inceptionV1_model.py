"""GoogLeNet model for Keras.

Related papers:
- https://arxiv.org/abs/1409.4842

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.keras import backend
from tensorflow.keras import models
from tensorflow.keras import regularizers
from tensorflow.keras import layers

L2_WEIGHT_DECAY = 1e-4


def inception_block(input_tensor,
                    num1x1,
                    num3x3_reduce,
                    num3x3,
                    num5x5_reduce,
                    num5x5,
                    pool_reduce,
                    stage,
                    block):
    """The inception block.

      Args:
        input_tensor: input tensor
        num1x1: integer, filters of 1x1 conv
        num3x3_reduce: integer, filters of 3x3 reduce
        num3x3: integer, filters of 3x3 conv
        num5x5_reduce: integer, filters of 5x5 reduce
        num5x5: integer, filters of 5x5 conv
        pool_reduce: integer, filters of pool reduce
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names

      Returns:
        Output tensor for the block.
    """

    if backend.image_data_format() == 'channels_last':
        channel_axis = -1
    else:
        channel_axis = 1

    name_base = str(stage) + block

    branch1x1 = layers.Conv2D(
        filters=num1x1,
        kernel_size=(1, 1),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_conv1x1')(input_tensor)
    branch1x1 = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_bn1x1')(branch1x1)
    branch1x1 = layers.Activation('relu')(branch1x1)

    branch3x3 = layers.Conv2D(
        filters=num3x3_reduce,
        kernel_size=(1, 1),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_conv3x3_reduce')(input_tensor)
    branch3x3 = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_bn3x3_reduce')(branch3x3)
    branch3x3 = layers.Activation('relu')(branch3x3)
    branch3x3 = layers.Conv2D(
        filters=num3x3,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_conv3x3')(branch3x3)
    branch3x3 = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_bn3x3')(branch3x3)
    branch3x3 = layers.Activation('relu')(branch3x3)

    branch5x5 = layers.Conv2D(
        filters=num5x5_reduce,
        kernel_size=(1, 1),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_conv5x5_reduce')(input_tensor)
    branch5x5 = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_bn5x5_reduce')(branch5x5)
    branch5x5 = layers.Activation('relu')(branch5x5)
    branch5x5 = layers.Conv2D(
        filters=num5x5,
        kernel_size=(5, 5),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_conv5x5')(branch5x5)
    branch5x5 = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_bn5x5')(branch5x5)
    branch5x5 = layers.Activation('relu')(branch5x5)

    branch_pool = layers.MaxPool2D(
        pool_size=(3, 3),
        strides=(1, 1),
        padding='same')(input_tensor)
    branch_pool = layers.Conv2D(
        filters=pool_reduce,
        kernel_size=(1, 1),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name=name_base + '_pool_reduce')(branch_pool)
    branch_pool = layers.BatchNormalization(
        axis=channel_axis,
        name=name_base + '_pool_bn')(branch_pool)
    branch_pool = layers.Activation('relu')(branch_pool)

    x = layers.Concatenate(axis=channel_axis)([branch1x1, branch3x3, branch5x5, branch_pool])

    return x


def inceptionV1(num_classes,
                batch_size=None):
    """Instantiates the GoogLeNet architecture.

    Arguments:
        num_classes: `int` number of classes for image classification.
        batch_size: Size of the batches for each step.

    Returns:
        A Keras model instance.
    """
    input_shape = (224, 224, 3)
    img_input = layers.Input(shape=input_shape, batch_size=batch_size)
    x = img_input

    if backend.image_data_format() == 'channels_first':
        x = layers.Permute((3, 1, 2))(x)
        bn_axis = 1
    else:  # channels_last
        bn_axis = -1

    # stage1
    x = layers.Conv2D(
        filters=64,
        kernel_size=(7, 7),
        strides=(2, 2),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name='stage1_conv7x7')(x)
    x = layers.BatchNormalization(
        axis=bn_axis,
        name='stage1_bn7x7')(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPool2D(
        pool_size=(3, 3),
        strides=(2, 2),
        padding='same')(x)

    # stage2
    x = layers.Conv2D(
        filters=64,
        kernel_size=(1, 1),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name='stage2_conv3x3_reduce')(x)
    x = layers.BatchNormalization(
        axis=bn_axis,
        name='stage2_bn3x3_reduce')(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(
        filters=192,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding='same',
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name='stage2_conv3x3')(x)
    x = layers.BatchNormalization(
        axis=bn_axis,
        name='stage2_bn3x3')(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPool2D(
        pool_size=(3, 3),
        strides=(2, 2),
        padding='same')(x)

    # stage3a
    x = inception_block(
        input_tensor=x,
        num1x1=64,
        num3x3_reduce=96,
        num3x3=128,
        num5x5_reduce=16,
        num5x5=32,
        pool_reduce=32,
        stage=3,
        block='a')

    # stage3b
    x = inception_block(
        input_tensor=x,
        num1x1=128,
        num3x3_reduce=128,
        num3x3=192,
        num5x5_reduce=32,
        num5x5=96,
        pool_reduce=64,
        stage=3,
        block='b')

    x = layers.MaxPool2D(
        pool_size=(3, 3),
        strides=(2, 2),
        padding='same')(x)

    # stage4a
    x = inception_block(
        input_tensor=x,
        num1x1=192,
        num3x3_reduce=96,
        num3x3=208,
        num5x5_reduce=16,
        num5x5=48,
        pool_reduce=64,
        stage=4,
        block='a')

    # stage4b
    x = inception_block(
        input_tensor=x,
        num1x1=160,
        num3x3_reduce=112,
        num3x3=224,
        num5x5_reduce=24,
        num5x5=64,
        pool_reduce=64,
        stage=4,
        block='b')

    # stage4c
    x = inception_block(
        input_tensor=x,
        num1x1=128,
        num3x3_reduce=128,
        num3x3=256,
        num5x5_reduce=24,
        num5x5=64,
        pool_reduce=64,
        stage=4,
        block='c')

    # stage4d
    x = inception_block(
        input_tensor=x,
        num1x1=112,
        num3x3_reduce=144,
        num3x3=288,
        num5x5_reduce=32,
        num5x5=64,
        pool_reduce=64,
        stage=4,
        block='d')

    # stage4e
    x = inception_block(
        input_tensor=x,
        num1x1=256,
        num3x3_reduce=160,
        num3x3=320,
        num5x5_reduce=32,
        num5x5=128,
        pool_reduce=128,
        stage=4,
        block='e')

    x = layers.MaxPool2D(
        pool_size=(3, 3),
        strides=(2, 2),
        padding='same')(x)

    # stage5a
    x = inception_block(
        input_tensor=x,
        num1x1=256,
        num3x3_reduce=160,
        num3x3=320,
        num5x5_reduce=32,
        num5x5=128,
        pool_reduce=128,
        stage=5,
        block='a')

    # stage5b
    x = inception_block(
        input_tensor=x,
        num1x1=384,
        num3x3_reduce=192,
        num3x3=384,
        num5x5_reduce=48,
        num5x5=128,
        pool_reduce=128,
        stage=5,
        block='b')

    # classifier
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(rate=0.4)(x)
    x = layers.Dense(
        units=num_classes,
        kernel_initializer='he_normal',
        kernel_regularizer=regularizers.l2(L2_WEIGHT_DECAY),
        name='fc1000')(x)

    # A softmax that is followed by the model loss must be done cannot be done
    # in float16 due to numeric issues. So we pass dtype=float32.
    x = layers.Activation('softmax', dtype='float32')(x)

    # Create model.
    return models.Model(img_input, x, name='googlenet')
