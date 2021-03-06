#!/usr/bin/env python3
import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """

    # Assign required parts of model to variables
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    #  Use tf.saved_model.loader.load to load the model and weights
    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    # Reads MetaGraphDef loaded by model, returns most recent saved computation of graph
    graph = tf.get_default_graph()
    # Allows us to call individual layers to train by name
    image_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer3_out = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer4_out = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer7_out = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)
    # Return layers for training while the rest remain frozen
    return image_input, keep_prob, layer3_out, layer4_out, layer7_out
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # Initialize weights with random normal distribution
    init = tf.random_normal_initializer(stddev = 0.001)
    # Set boundary of regularizer
    reg = tf.contrib.layers.l2_regularizer(.00001)

    conv3 = tf.layers.conv2d(vgg_layer3_out, num_classes, 1, padding='same',
                            kernel_initializer=init, kernel_regularizer=reg)

    conv4 = tf.layers.conv2d(vgg_layer4_out, num_classes, 1, padding='same',
                            kernel_initializer=init, kernel_regularizer=reg)

    conv7 = tf.layers.conv2d(vgg_layer7_out, num_classes, 1, padding='same',
                            kernel_initializer=init, kernel_regularizer=reg)

    transp1 = tf.layers.conv2d_transpose(conv7, num_classes, 4, 2, padding='same',
                                kernel_initializer=init, kernel_regularizer=reg)

    skip1 = tf.add(transp1, conv4)

    transp2 = tf.layers.conv2d_transpose(skip1, num_classes, 4, 2, padding='same',
                                            kernel_initializer=init, kernel_regularizer=reg)

    skip2 = tf.add(transp2, conv3)

    output = tf.layers.conv2d_transpose(skip2, num_classes, 16, 8, padding='same',
                                        kernel_initializer=init, kernel_regularizer=reg)

    return output
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # reshape data
    logits = tf.reshape(nn_last_layer, (-1, num_classes))

    labels = tf.reshape(correct_label, (-1, num_classes))

    cross_entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits,
                                                                                labels=labels))
    
    train_op = tf.train.AdamOptimizer(learning_rate).minimize(cross_entropy_loss)

    return logits, train_op, cross_entropy_loss
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """

    for e in range(epochs):
        for i, (img, label) in enumerate(get_batches_fn(batch_size)):
            _, loss = sess.run([train_op, cross_entropy_loss],
                                feed_dict={input_image:img, correct_label:label, keep_prob:0.5, learning_rate:.00033})

            print("Epoch: {}\tBatch: {}\tLoss: {}".format(e+1, i, loss))
tests.test_train_nn(train_nn)


def run():
    EPOCHS = 20
    BATCH_SIZE = 16
    NUM_CLASSES = 2
    IMAGE_SHAPE = (160, 576)
    DATA_DIR = './data'
    CKPT_DIR = './runs'
    tests.test_for_kitti_dataset(DATA_DIR)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(DATA_DIR)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/
    gpu_config = tf.ConfigProto()
    #gpu_config.gpu_options.per_process_gpu_memory_fraction = .4
    gpu_config.gpu_options.allow_growth = True
    with tf.Session(config=gpu_config) as sess:
        # Path to vgg model
        vgg_path = os.path.join(DATA_DIR, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(DATA_DIR, 'data_road/training'), IMAGE_SHAPE)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # load training input, keep prob and layers
        input_image, keep_prob, layer3_out, layer4_out, layer7_out = load_vgg(sess, vgg_path)
        final_layer = layers(layer3_out, layer4_out, layer7_out, NUM_CLASSES)
        label = tf.placeholder(tf.int32, shape=[None, None, None, NUM_CLASSES], name='label')
        learning_rate = tf.placeholder(tf.float32, name='learning_rate')
        logits, train_op, loss = optimize(final_layer, label, learning_rate, NUM_CLASSES)
    
        saver = tf.train.Saver()
        #saver.restore(sess, './runs/sem_seg_model.ckpt')

        sess.run(tf.global_variables_initializer())
        train_nn(sess, EPOCHS, BATCH_SIZE, get_batches_fn, train_op, loss,
                input_image, label, keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        helper.save_inference_samples(CKPT_DIR, DATA_DIR, sess, IMAGE_SHAPE, logits, keep_prob, input_image)

        # OPTIONAL: Apply the trained model to a video

        saver.restore(sess, './runs/sem_seg_model.ckpt')

if __name__ == '__main__':
    run()
