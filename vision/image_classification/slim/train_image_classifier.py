"""Generic training script that trains a model using a given dataset."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags
from absl import logging

import tensorflow as tf
import tf_slim as slim

from vision.image_classification.slim.datasets import dataset_factory
from vision.image_classification.slim.deployment import model_deploy
from vision.image_classification.slim.nets import nets_factory
from vision.image_classification.slim.preprocessing import preprocessing_factory


def define_common_flags():
    flags.DEFINE_string(
        'master', '', 'The address of the TensorFlow master to use.')

    flags.DEFINE_string(
        'train_dir', '/tmp/tfmodel/',
        'Directory where checkpoints and event logs are written to.')
    flags.DEFINE_float(
        'warmup_epochs', 0,
        'Linearly warmup learning rate from 0 to learning_rate over this '
        'many epochs.')

    flags.DEFINE_integer('num_clones', 1,
                         'Number of model clones to deploy. Note For '
                         'historical reasons loss from all clones averaged '
                         'out and learning rate decay happen per clone '
                         'epochs')

    flags.DEFINE_boolean('clone_on_cpu', False,
                         'Use CPUs to deploy clones.')

    flags.DEFINE_integer('worker_replicas', 1, 'Number of worker replicas.')

    flags.DEFINE_integer(
        'num_ps_tasks', 0,
        'The number of parameter servers. If the value is 0, then the parameters '
        'are handled locally by the worker.')

    flags.DEFINE_integer(
        'num_readers', 4,
        'The number of parallel readers that read data from the dataset.')

    flags.DEFINE_integer(
        'num_preprocessing_threads', 4,
        'The number of threads used to create the batches.')

    flags.DEFINE_integer(
        'log_every_n_steps', 10,
        'The frequency with which logs are print.')

    flags.DEFINE_integer(
        'save_summaries_secs', 600,
        'The frequency with which summaries are saved, in seconds.')

    flags.DEFINE_integer(
        'save_interval_secs', 600,
        'The frequency with which the model is saved, in seconds.')

    flags.DEFINE_integer(
        'task', 0, 'Task id of the replica running the training.')


def define_optimization_flags():
    flags.DEFINE_float(
        'weight_decay', 0.00004, 'The weight decay on the model weights.')

    flags.DEFINE_string(
        'optimizer', 'rmsprop',
        'The name of the optimizer, one of "adadelta", "adagrad", "adam",'
        '"ftrl", "momentum", "sgd" or "rmsprop".')

    flags.DEFINE_float(
        'adadelta_rho', 0.95,
        'The decay rate for adadelta.')

    flags.DEFINE_float(
        'adagrad_initial_accumulator_value', 0.1,
        'Starting value for the AdaGrad accumulators.')

    flags.DEFINE_float(
        'adam_beta1', 0.9,
        'The exponential decay rate for the 1st moment estimates.')

    flags.DEFINE_float(
        'adam_beta2', 0.999,
        'The exponential decay rate for the 2nd moment estimates.')

    flags.DEFINE_float('opt_epsilon', 1.0, 'Epsilon term for the optimizer.')

    flags.DEFINE_float('ftrl_learning_rate_power', -0.5,
                       'The learning rate power.')

    flags.DEFINE_float(
        'ftrl_initial_accumulator_value', 0.1,
        'Starting value for the FTRL accumulators.')

    flags.DEFINE_float(
        'ftrl_l1', 0.0, 'The FTRL l1 regularization strength.')

    flags.DEFINE_float(
        'ftrl_l2', 0.0, 'The FTRL l2 regularization strength.')

    flags.DEFINE_float(
        'momentum', 0.9,
        'The momentum for the MomentumOptimizer and RMSPropOptimizer.')

    flags.DEFINE_float('rmsprop_momentum', 0.9, 'Momentum.')

    flags.DEFINE_float('rmsprop_decay', 0.9, 'Decay term for RMSProp.')


def define_lr_flags():
    flags.DEFINE_string(
        'learning_rate_decay_type',
        'exponential',
        'Specifies how the learning rate is decayed. One of "fixed", "exponential",'
        ' or "polynomial"')

    flags.DEFINE_float('learning_rate', 0.01, 'Initial learning rate.')

    flags.DEFINE_float(
        'end_learning_rate', 0.0001,
        'The minimal end learning rate used by a polynomial decay learning rate.')

    flags.DEFINE_float(
        'label_smoothing', 0.0, 'The amount of label smoothing.')

    flags.DEFINE_float(
        'learning_rate_decay_factor', 0.94, 'Learning rate decay factor.')

    flags.DEFINE_float(
        'num_epochs_per_decay', 2.0,
        'Number of epochs after which learning rate decays. Note: this flag counts '
        'epochs per clone but aggregates per sync replicas. So 1.0 means that '
        'each clone will go over full epoch individually, but replicas will go '
        'once across all replicas.')

    flags.DEFINE_bool(
        'sync_replicas', False,
        'Whether or not to synchronize the replicas during training.')

    flags.DEFINE_integer(
        'replicas_to_aggregate', 1,
        'The Number of gradients to collect before updating params.')

    flags.DEFINE_float(
        'moving_average_decay', None,
        'The decay to use for the moving average.'
        'If left as None, then moving averages are not used.')


def define_dataset_flags():
    flags.DEFINE_string(
        'dataset_name', 'imagenet', 'The name of the dataset to load.')

    flags.DEFINE_string(
        'dataset_split_name', 'train', 'The name of the train/test split.')

    flags.DEFINE_string(
        'dataset_dir', '/data/imagenet/tfrecord', 'The directory where the dataset files are stored.')

    flags.DEFINE_integer(
        'labels_offset', 0,
        'An offset for the labels in the dataset. This flag is primarily used to '
        'evaluate the VGG and ResNet architectures which do not use a background '
        'class for the ImageNet dataset.')

    flags.DEFINE_string(
        'model_name', 'inception_v3', 'The name of the architecture to train.')

    flags.DEFINE_string(
        'preprocessing_name', None, 'The name of the preprocessing to use. If left '
                                    'as `None`, then the model_name flag is used.')

    flags.DEFINE_integer(
        'batch_size', 32, 'The number of samples in each batch.')

    flags.DEFINE_integer(
        'train_image_size', None, 'Train image size')

    flags.DEFINE_integer('max_number_of_steps', None,
                         'The maximum number of training steps.')

    flags.DEFINE_bool('use_grayscale', False,
                      'Whether to convert input images to grayscale.')


def define_fine_tuning_flags():
    flags.DEFINE_string(
        'checkpoint_path', None,
        'The path to a checkpoint from which to fine-tune.')

    flags.DEFINE_string(
        'checkpoint_exclude_scopes', None,
        'Comma-separated list of scopes of variables to exclude when restoring '
        'from a checkpoint.')

    flags.DEFINE_string(
        'trainable_scopes', None,
        'Comma-separated list of scopes to filter the set of variables to train.'
        'By default, None would train all the variables.')

    flags.DEFINE_boolean(
        'ignore_missing_vars', False,
        'When restoring a checkpoint would ignore missing variables.')


def define_classifier_flags():
    define_common_flags()
    define_optimization_flags()
    define_lr_flags()
    define_dataset_flags()
    define_fine_tuning_flags()


def _configure_learning_rate(num_samples_per_epoch, global_step):
    """Configures the learning rate.

    Args:
      num_samples_per_epoch: The number of samples in each epoch of training.
      global_step: The global_step tensor.

    Returns:
      A `Tensor` representing the learning rate.

    Raises:
      ValueError: if
    """
    # Note: when num_clones is > 1, this will actually have each clone to go
    # over each epoch FLAGS.num_epochs_per_decay times. This is different
    # behavior from sync replicas and is expected to produce different results.
    FLAGS = flags.FLAGS
    steps_per_epoch = num_samples_per_epoch / FLAGS.batch_size
    if FLAGS.sync_replicas:
        steps_per_epoch /= FLAGS.replicas_to_aggregate

    decay_steps = int(steps_per_epoch * FLAGS.num_epochs_per_decay)

    if FLAGS.learning_rate_decay_type == 'exponential':
        learning_rate = tf.compat.v1.train.exponential_decay(
            FLAGS.learning_rate,
            global_step,
            decay_steps,
            FLAGS.learning_rate_decay_factor,
            staircase=True,
            name='exponential_decay_learning_rate')
    elif FLAGS.learning_rate_decay_type == 'fixed':
        learning_rate = tf.constant(FLAGS.learning_rate, name='fixed_learning_rate')
    elif FLAGS.learning_rate_decay_type == 'polynomial':
        learning_rate = tf.compat.v1.train.polynomial_decay(
            FLAGS.learning_rate,
            global_step,
            decay_steps,
            FLAGS.end_learning_rate,
            power=1.0,
            cycle=False,
            name='polynomial_decay_learning_rate')
    else:
        raise ValueError('learning_rate_decay_type [%s] was not recognized' %
                         FLAGS.learning_rate_decay_type)

    if FLAGS.warmup_epochs:
        warmup_lr = (
                FLAGS.learning_rate * tf.cast(global_step, tf.float32) /
                (steps_per_epoch * FLAGS.warmup_epochs))
        learning_rate = tf.minimum(warmup_lr, learning_rate)
    return learning_rate


def _configure_optimizer(learning_rate):
    """Configures the optimizer used for training.

    Args:
      learning_rate: A scalar or `Tensor` learning rate.

    Returns:
      An instance of an optimizer.

    Raises:
      ValueError: if FLAGS.optimizer is not recognized.
    """
    FLAGS = flags.FLAGS
    if FLAGS.optimizer == 'adadelta':
        optimizer = tf.compat.v1.train.AdadeltaOptimizer(
            learning_rate,
            rho=FLAGS.adadelta_rho,
            epsilon=FLAGS.opt_epsilon)
    elif FLAGS.optimizer == 'adagrad':
        optimizer = tf.compat.v1.train.AdagradOptimizer(
            learning_rate,
            initial_accumulator_value=FLAGS.adagrad_initial_accumulator_value)
    elif FLAGS.optimizer == 'adam':
        optimizer = tf.keras.optimizers.Adam(
            learning_rate,
            beta1=FLAGS.adam_beta1,
            beta2=FLAGS.adam_beta2,
            epsilon=FLAGS.opt_epsilon)
    elif FLAGS.optimizer == 'ftrl':
        optimizer = tf.compat.v1.train.FtrlOptimizer(
            learning_rate,
            learning_rate_power=FLAGS.ftrl_learning_rate_power,
            initial_accumulator_value=FLAGS.ftrl_initial_accumulator_value,
            l1_regularization_strength=FLAGS.ftrl_l1,
            l2_regularization_strength=FLAGS.ftrl_l2)
    elif FLAGS.optimizer == 'momentum':
        optimizer = tf.compat.v1.train.MomentumOptimizer(
            learning_rate,
            momentum=FLAGS.momentum,
            name='Momentum')
    elif FLAGS.optimizer == 'rmsprop':
        optimizer = tf.compat.v1.train.RMSPropOptimizer(
            learning_rate,
            decay=FLAGS.rmsprop_decay,
            momentum=FLAGS.rmsprop_momentum,
            epsilon=FLAGS.opt_epsilon)
    elif FLAGS.optimizer == 'sgd':
        optimizer = tf.compat.v1.train.GradientDescentOptimizer(learning_rate)
    else:
        raise ValueError('Optimizer [%s] was not recognized' % FLAGS.optimizer)
    return optimizer


def _get_init_fn():
    """Returns a function run by the chief worker to warm-start the training.

    Note that the init_fn is only run when initializing the model during the very
    first global step.

    Returns:
      An init function run by the supervisor.
    """
    FLAGS = flags.FLAGS
    if FLAGS.checkpoint_path is None:
        return None

    # Warn the user if a checkpoint exists in the train_dir. Then we'll be
    # ignoring the checkpoint anyway.
    if tf.train.latest_checkpoint(FLAGS.train_dir):
        tf.compat.v1.logging.info(
            'Ignoring --checkpoint_path because a checkpoint already exists in %s'
            % FLAGS.train_dir)
        return None

    exclusions = []
    if FLAGS.checkpoint_exclude_scopes:
        exclusions = [scope.strip()
                      for scope in FLAGS.checkpoint_exclude_scopes.split(',')]

    # TODO(sguada) variables.filter_variables()
    variables_to_restore = []
    for var in slim.get_model_variables():
        for exclusion in exclusions:
            if var.op.name.startswith(exclusion):
                break
        else:
            variables_to_restore.append(var)

    if tf.io.gfile.isdir(FLAGS.checkpoint_path):
        checkpoint_path = tf.train.latest_checkpoint(FLAGS.checkpoint_path)
    else:
        checkpoint_path = FLAGS.checkpoint_path

    logging.info('Fine-tuning from %s' % checkpoint_path)

    return slim.assign_from_checkpoint_fn(
        checkpoint_path,
        variables_to_restore,
        ignore_missing_vars=FLAGS.ignore_missing_vars)


def _get_variables_to_train():
    """Returns a list of variables to train.

    Returns:
      A list of variables to train by the optimizer.
    """
    FLAGS = flags.FLAGS
    if FLAGS.trainable_scopes is None:
        return tf.compat.v1.trainable_variables()
    else:
        scopes = [scope.strip() for scope in FLAGS.trainable_scopes.split(',')]

    variables_to_train = []
    for scope in scopes:
        variables = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.TRAINABLE_VARIABLES, scope)
        variables_to_train.extend(variables)
    return variables_to_train


def main(_):
    FLAGS = flags.FLAGS
    if not FLAGS.dataset_dir:
        raise ValueError('You must supply the dataset directory with --dataset_dir')

    with tf.Graph().as_default():
        #######################
        # Config model_deploy #
        #######################
        deploy_config = model_deploy.DeploymentConfig(
            num_clones=FLAGS.num_clones,
            clone_on_cpu=FLAGS.clone_on_cpu,
            replica_id=FLAGS.task,
            num_replicas=FLAGS.worker_replicas,
            num_ps_tasks=FLAGS.num_ps_tasks)

        # Create global_step
        with tf.device(deploy_config.variables_device()):
            global_step = slim.create_global_step()

        ######################
        # Select the dataset #
        ######################
        dataset = dataset_factory.get_dataset(
            FLAGS.dataset_name, FLAGS.dataset_split_name, FLAGS.dataset_dir)

        ######################
        # Select the network #
        ######################
        network_fn = nets_factory.get_network_fn(
            FLAGS.model_name,
            num_classes=(dataset.num_classes - FLAGS.labels_offset),
            weight_decay=FLAGS.weight_decay,
            is_training=True)

        #####################################
        # Select the preprocessing function #
        #####################################
        preprocessing_name = FLAGS.preprocessing_name or FLAGS.model_name
        image_preprocessing_fn = preprocessing_factory.get_preprocessing(
            preprocessing_name,
            is_training=True,
            use_grayscale=FLAGS.use_grayscale)

        ##############################################################
        # Create a dataset provider that loads data from the dataset #
        ##############################################################
        with tf.device(deploy_config.inputs_device()):
            provider = slim.dataset_data_provider.DatasetDataProvider(
                dataset,
                num_readers=FLAGS.num_readers,
                common_queue_capacity=20 * FLAGS.batch_size,
                common_queue_min=10 * FLAGS.batch_size)
            [image, label] = provider.get(['image', 'label'])
            label -= FLAGS.labels_offset

            train_image_size = FLAGS.train_image_size or network_fn.default_image_size

            image = image_preprocessing_fn(image, train_image_size, train_image_size)

            images, labels = tf.compat.v1.train.batch(
                [image, label],
                batch_size=FLAGS.batch_size,
                num_threads=FLAGS.num_preprocessing_threads,
                capacity=5 * FLAGS.batch_size)
            labels = slim.one_hot_encoding(
                labels, dataset.num_classes - FLAGS.labels_offset)
            batch_queue = slim.prefetch_queue.prefetch_queue(
                [images, labels], capacity=2 * deploy_config.num_clones)

        ####################
        # Define the model #
        ####################
        def clone_fn(batch_queue):
            """Allows data parallelism by creating multiple clones of network_fn."""
            images, labels = batch_queue.dequeue()
            logits, end_points = network_fn(images)

            #############################
            # Specify the loss function #
            #############################
            if 'AuxLogits' in end_points:
                slim.losses.softmax_cross_entropy(
                    end_points['AuxLogits'], labels,
                    label_smoothing=FLAGS.label_smoothing, weights=0.4,
                    scope='aux_loss')
            slim.losses.softmax_cross_entropy(
                logits, labels, label_smoothing=FLAGS.label_smoothing, weights=1.0)
            return end_points

        # Gather initial summaries.
        summaries = set(tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.SUMMARIES))

        clones = model_deploy.create_clones(deploy_config, clone_fn, [batch_queue])
        first_clone_scope = deploy_config.clone_scope(0)
        # Gather update_ops from the first clone. These contain, for example,
        # the updates for the batch_norm variables created by network_fn.
        update_ops = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.UPDATE_OPS, first_clone_scope)

        # Add summaries for end_points.
        end_points = clones[0].outputs
        for end_point in end_points:
            x = end_points[end_point]
            summaries.add(tf.compat.v1.summary.histogram('activations/' + end_point, x))
            summaries.add(tf.compat.v1.summary.scalar('sparsity/' + end_point, tf.nn.zero_fraction(x)))

        # Add summaries for losses.
        for loss in tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.LOSSES, first_clone_scope):
            summaries.add(tf.compat.v1.summary.scalar('losses/%s' % loss.op.name, loss))

        # Add summaries for variables.
        for variable in slim.get_model_variables():
            summaries.add(tf.compat.v1.summary.histogram(variable.op.name, variable))

        #################################
        # Configure the moving averages #
        #################################
        if FLAGS.moving_average_decay:
            moving_average_variables = slim.get_model_variables()
            variable_averages = tf.train.ExponentialMovingAverage(
                FLAGS.moving_average_decay, global_step)
        else:
            moving_average_variables, variable_averages = None, None

        #########################################
        # Configure the optimization procedure. #
        #########################################
        with tf.device(deploy_config.optimizer_device()):
            learning_rate = _configure_learning_rate(dataset.num_samples, global_step)
            optimizer = _configure_optimizer(learning_rate)
            summaries.add(tf.compat.v1.summary.scalar('learning_rate', learning_rate))

        if FLAGS.sync_replicas:
            # If sync_replicas is enabled, the averaging will be done in the chief
            # queue runner.
            optimizer = tf.compat.v1.train.SyncReplicasOptimizer(
                opt=optimizer,
                replicas_to_aggregate=FLAGS.replicas_to_aggregate,
                total_num_replicas=FLAGS.worker_replicas,
                variable_averages=variable_averages,
                variables_to_average=moving_average_variables)
        elif FLAGS.moving_average_decay:
            # Update ops executed locally by trainer.
            update_ops.append(variable_averages.apply(moving_average_variables))

        # Variables to train.
        variables_to_train = _get_variables_to_train()

        #  and returns a train_tensor and summary_op
        total_loss, clones_gradients = model_deploy.optimize_clones(
            clones,
            optimizer,
            var_list=variables_to_train)
        # Add total_loss to summary.
        summaries.add(tf.compat.v1.summary.scalar('total_loss', total_loss))

        # Create gradient updates.
        grad_updates = optimizer.apply_gradients(clones_gradients,
                                                 global_step=global_step)
        update_ops.append(grad_updates)

        update_op = tf.group(*update_ops)
        with tf.control_dependencies([update_op]):
            train_tensor = tf.identity(total_loss, name='train_op')

        # Add the summaries from the first clone. These contain the summaries
        # created by model_fn and either optimize_clones() or _gather_clone_loss().
        summaries |= set(tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.SUMMARIES,
                                                     first_clone_scope))

        # Merge all summaries together.
        summary_op = tf.compat.v1.summary.merge(list(summaries), name='summary_op')

        ###########################
        # Kicks off the training. #
        ###########################
        slim.learning.train(
            train_tensor,
            logdir=FLAGS.train_dir,
            master=FLAGS.master,
            is_chief=(FLAGS.task == 0),
            init_fn=_get_init_fn(),
            summary_op=summary_op,
            number_of_steps=FLAGS.max_number_of_steps,
            log_every_n_steps=FLAGS.log_every_n_steps,
            save_summaries_secs=FLAGS.save_summaries_secs,
            save_interval_secs=FLAGS.save_interval_secs,
            sync_optimizer=optimizer if FLAGS.sync_replicas else None)


if __name__ == '__main__':
    logging.set_verbosity(logging.INFO)
    define_classifier_flags()

    app.run(main)
