from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
import os
import sys
import cv2
import numpy as np
import shutil
from data.config import settings  # pylint: disable=import-error
from Screenshot import Screenshot_Clipping
import boto3
from boto3.s3.transfer import S3Transfer
from botocore.exceptions import ClientError, ProfileNotFound
from aws_client.aws_client import AWSMapper

class VisualUtils():
    baseline_image = None
    actual_image = None 
    bflag = True

    def __init__(self, context, file_name, *locators):
        self.context = context
        self.file_name = file_name + '_%s_%s.png'
        self.locators = locators
        self.driver = context.driver
        self.baseline = context.baseline
        self.check_level = context.check_level
        self.resolution = context.device
        self.browser = context.browser
        self.project = (list(self.context.tags)[0].split('-'))[0]
        self.runner_instance = settings['runner_instance']
        self.results_settings = settings['results']
        self.test_data_folder = os.path.join(os.getcwd(),'visual-test-data' + os.sep)
        self.folder = self.test_data_folder+self.project+os.sep
        self.baseline_folder = self.folder + "baseline" + os.sep
        self.capture_screens()

    def __call__(self):
         return self.bflag

    def capture_screens(self):
        if not os.path.exists(self.baseline_folder):
            if not os.path.exists(self.test_data_folder):
                os.mkdir(self.test_data_folder)
            if not os.path.exists(self.folder):
                os.mkdir(self.folder)
            os.mkdir(self.baseline_folder)
        if self.resolution == 'default':
            default_res = self.driver.get_window_size()
            dimension = str(default_res['width'])+'_'+str(default_res['height'])
            file_name_suffix = self.file_name % (self.browser, str(dimension))
        else:
            file_name_suffix = self.file_name % (self.browser, self.resolution)
        if self.baseline:
            self.baseline_image = self.screenshot(self.baseline_folder, file_name_suffix)
            self.store_baseline_s3(file_name_suffix)
            self.bflag = True
        else:
            self.actual_image = self.screenshot(self.folder, file_name_suffix)
            self.get_baseline_s3(file_name_suffix)
            self.compare_screenshots()
            
    def screenshot(self, path, file_name):
        folder_path = os.path.join(path, file_name)
        Screenshot_Clipping.Screenshot().full_Screenshot(self.context.driver, path, file_name)
        return folder_path

    def compare_screenshots(self):
        try:
            region_baseline = []
            region_actual = []
            bounding_rect = []
            baseline_temp = self.baseline_folder+self.file_name % (self.browser, self.resolution+'_temp')
            actual_temp = self.folder+self.file_name % (self.browser, self.resolution+'_temp')
            shutil.copy(self.actual_image, actual_temp)
            shutil.copy(self.baseline_image, baseline_temp)
            if self.check_level == 'layout':
        
                self.bounding_rect_text_area(baseline_temp)
                self.bounding_rect_text_area(actual_temp)
            
            if self.locators:
                for element in self.locators:
                    for x in range(len(element)): 
                        bounding_rect.append([element[x]['x'], element[x]['y'],
                                    element[x]['width'], element[x]['height']])
                    self.mask_bounding_rect(bounding_rect, actual_temp)
                    self.mask_bounding_rect(bounding_rect, baseline_temp)

            screenshot_baseline = Image.open(baseline_temp)
            screenshot_actual = Image.open(actual_temp)
            screenshot_actual_prod = Image.open(self.actual_image)
            columns = 150
            rows = 90
            screen_width, screen_height = screenshot_baseline.size
            block_width = ((screen_width - 1) // columns) + 1 # this is just a division ceiling
            block_height = ((screen_height - 1) // rows) + 1

            for y in range(0, screen_height, block_height+1):
                for x in range(0, screen_width, block_width + 1):
                    region_baseline = self.pixel_data(screenshot_baseline, x, y, block_width, block_height)
                    region_actual = self.pixel_data(screenshot_actual, x, y, block_width, block_height)
                   
                    if region_baseline is not None and region_actual is not None and region_baseline != region_actual and region_baseline[1] != (255, 0, 255) and region_actual[1] != (255, 0, 255):
                        draw = ImageDraw.Draw(screenshot_actual_prod)
                        draw.rectangle((x, y, x + block_width, y + block_height), outline="red")
                        self.bflag = False

            screenshot_actual_prod.save(self.actual_image)
            self.context.actual_image = self.actual_image
            self.context.baseline_image = self.baseline_image
            os.remove(baseline_temp)
            os.remove(actual_temp)
        except Exception as e:
            print(str(e))
        return self.bflag

    def pixel_data(self, image, x, y, width, height):
        region_total = 0
        reg_fact = ()
        # Sensitive factor
        factor = 10
        for coordinate_y in range(y, y+height):
            for coordinate_x in range(x, x+width):
                try:
                    pixel = image.getpixel((coordinate_x, coordinate_y))
                    region_total += sum(pixel)/4
                except:
                    return
                
        reg_fact = (region_total / factor, pixel)
        return reg_fact

    def bounding_rect_text_area(self, img):
        bound_rect_list = []
        cv_image=cv2.imread(img)
        cv_image.copy()
        g_image=cv2.cvtColor(cv_image,cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(g_image,(1,1),0)
        ret, th = cv2.threshold(blur,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        contours, histo = cv2.findContours(th,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
                [x, y, w, h] = cv2.boundingRect(contour)

                if h > 20:
                    continue
                bound_rect_list.append([x, y, w, h])
        self.mask_bounding_rect(bound_rect_list, img)

    def mask_bounding_rect(self, bound_rect_list, img):
        pil_img = Image.open(img)
        draw = ImageDraw.Draw(pil_img)
        for bound_rect in bound_rect_list:
            draw.rectangle((bound_rect[0], bound_rect[1], bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3]), fill = (255, 0, 255, 255))
        pil_img.save(img)

    def store_baseline_s3(self, filename):
        try:
            s3 = S3Transfer(AWSMapper().client('s3'))
            s3.upload_file(self.baseline_image,
                self.results_settings['bucket'].get('name', 'emisx-gui-test-result-prd'), 'visual-test-baseline/' +
                self.project+'/'+self.resolution+'/'+filename)
        except ClientError as e:
            print("Unable to download baseline from s3 as {}".format(str(e)))
            raise ClientError(e.response['Error'], e.operation_name)

    def get_baseline_s3(self, filename):
        try:
            s3 = S3Transfer(AWSMapper().client('s3'))
            bucket = self.results_settings['bucket'].get('name', 'emisx-gui-test-result-prd')
            folder = 'visual-test-baseline/' + self.project + '/' + self.resolution + '/' + filename
            self.baseline_image = self.folder+'baseline/'+filename
            s3.download_file(bucket, folder, self.baseline_image)
        except ClientError as e:
                print("Unable to download baseline from s3 as {}".format(str(e)))
                raise ClientError(e.response['Error'], e.operation_name)