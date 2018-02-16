# classify img arrays
from __future__ import print_function
import numpy as np
import tensorflow as tf
import pandas as pa
from models.dwd_net import build_dwd_net
from class_utils.dws_transform import perform_dws
import os.path as osp

class dws_detector:
    model_path = "trained_models"
    model_name = "RefineNet-Res101"
    mapping_name = "mappings.csv"
    seed = 123
    tf_session = None
    mapping = None
    overlap = 20
    root_dir = osp.abspath(osp.join(osp.dirname(__file__), '..'))

    patch_size = [640, 640]

    def __init__(self):
        np.random.seed(self.seed)
        tf.set_random_seed(self.seed)

        print('Loading mappings ...')
        mapping = pa.read_csv(self.root_dir + "/" + self.mapping_name)
        mapping = mapping[mapping["Init_name"] != "-1"]
        mapping = mapping.drop(mapping.columns[[0, 2]], axis=1)

        # strip values
        mapping['Init_name'] = mapping['Init_name'].str.strip()

        # reset index
        self.mapping = mapping.reset_index(drop=True)

        sess = tf.Session()
        print('Loading model')
        self.input = tf.placeholder(tf.float32, shape=[None, None, None, 1])
        [self.dws_energy, self.class_logits, self.bbox_size], init_fn = build_dwd_net(self.input, model=self.model_name, num_classes=len(self.mapping), pretrained_dir="", substract_mean=False)
        saver = tf.train.Saver(max_to_keep=1000)
        sess.run(tf.global_variables_initializer())
        print("Loading weights")
        saver.restore(sess, self.root_dir+"/" +self.model_path + "/" + self.model_name)
        self.tf_session = sess

    def classify_img(self, img):
        print("classify")
        if len(img.shape) < 4:
            img = np.expand_dims(np.expand_dims(img,-1),0)
        # offsets = dict(y = [-self.overlap], x = [-self.overlap])
        # while max(offsets["y"]) < img.shape[0]:
        #     offsets["y"].append(max(offsets["y"])+self.patch_size)
        # pad both axes to multiples of 320
        y_mulity = int(np.ceil(img.shape[1]/320.0))
        x_mulity = int(np.ceil(img.shape[2] / 320.0))
        canv = np.ones([y_mulity*320,x_mulity*320], dtype=np.uint8)*255
        canv = np.expand_dims(np.expand_dims(canv, -1), 0)

        canv[0,0:img.shape[1],0:img.shape[2]] = img[0]
        pred_energy, pred_class_logits, pred_bbox = self.tf_session.run(
            [self.dws_energy, self.class_logits, self.bbox_size],
            feed_dict={self.input: canv})
        pred_class = np.argmax(pred_class_logits, axis=3)

        dws_list = perform_dws(pred_energy, pred_class, pred_bbox)

        # dws_list, img = perform_dws(pred_energy, pred_class, pred_bbox, return_ccomp_img=True)
        # from PIL import Image
        # img.show()
        # binar_energy = (pred_energy <= 0) * 255
        # data_img = Image.fromarray(np.squeeze(binar_energy).astype(np.uint8))
        # data_img.show()

        for element in dws_list:
            element[4] = self.mapping.iloc[element[4]]["Symbol ID"]

        return dws_list


def show_image(data, gt_boxes=None, gt=False, text=False):
    from PIL import ImageDraw
    im = Image.fromarray(data[0].astype("uint8"))
    im.show()

    if gt:
        draw = ImageDraw.Draw(im)
        # overlay GT boxes
        for row in gt_boxes:
            draw.rectangle(((row[0],row[1]),(row[2],row[3])), fill="red")
        #im.show()
    if text:
        draw = ImageDraw.Draw(im)
        # overlay GT boxes
        for row in gt_boxes:
            draw.text((row[2],row[3]),row[4], fill="red")
        im.show()

    return


if __name__ == '__main__':
    detection = dws_detector()
    from PIL import Image
    import cv2
    pic = Image.open("demo/lg-9997209-aug-beethoven--page-2.png").convert('L')
    pic = np.asanyarray(pic)
    im = cv2.resize(pic, None, None, fx=0.5, fy=0.5,interpolation=cv2.INTER_LINEAR)

    bboxes = detection.classify_img(im)
    show_image([np.asanyarray(im)], bboxes, True, True)
    print("testing mode")
