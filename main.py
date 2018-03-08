from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from camera_d3 import CameraD3
from camera_d3 import Histogram
from camera_d3 import ImageButton
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.togglebutton import Button
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.image import Image
from kivy.garden.graph import Graph, MeshLinePlot, MeshStemPlot
from kivy.uix.slider import Slider
from kivy.uix.progressbar import ProgressBar
from kivy.graphics.transformation import Matrix
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from time import sleep
from threading import Thread
import matplotlib

from kivy.app import App
from kivy.uix.carousel import Carousel
from kivy.uix.image import AsyncImage

matplotlib.use('module://kivy.garden.matplotlib.backend_kivyagg')
from matplotlib import pyplot as plt
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
from time import sleep
import time
import datetime
import numpy as np
import cv2
from cv2 import cv
import dropbox
import os
import sys

import RPi.GPIO as GPIO

LED_Pin = 19 # Broadcom Pin 4

class TestCamera(App):
    def __init__(self, **kwargs):
        super(TestCamera, self).__init__(**kwargs)
        self._camera = None

    def _camera_toggle(self, val):
        self._camera.play = not self._camera.play

    def _led_toggle(self, val):
        if self._led_state == GPIO.LOW:
            self._led_state = GPIO.HIGH
            self._toggle.text = "LED ON"
        else:
            self._led_state = GPIO.LOW
            self._toggle.text = "LED OFF"
        GPIO.output(LED_Pin, self._led_state)



    def _show_demo_results(self, val):
        popup = Popup(title='Reconstruction Results',
                      content=Label(text=
                        'TOTAL TARGET CELLS                          : 52\n'+
                        'TOTAL FOUND  CELLS                           : 77\n'+
                        'TOTAL FILTERED CELLS                        : 0\n'+
                        'TOTAL BEADS FOR TARGET CELLS      : 235\n'+
                        'AVERAGE BEADS/CELL                         : 4'),
                      size_hint=(None, None), size=(400, 200))
        popup.open()

    def _show_carousel(self, log_file):
        local_recon = '/home/pi/recon'
        prefix = log_file.split('.', 1)[0]
        carousel = Carousel(direction='right')
        for filename in os.listdir(local_recon):
            if filename.startswith(prefix) and filename.endswith('.png'):
                src = os.path.join(local_recon, filename)
                image = Image(source=src, allow_stretch=True,  size=(620, 460))
                carousel.add_widget(image)
        popup = Popup(title='Reconstruction Results',
                      content=carousel,
                      size_hint=(None, None), size=(640, 480))
        popup.open()


    def _request_capture(self, val):
        self._camera.capture__full_res_frame()

    def _request_ref_capture(self, val):
        self._camera.capture__full_res_ref()


    def _toggle_object_detection(self, val):
        detecting = not self._camera.get_object_detection()
        self._camera.set_object_detection(detecting)
        if not detecting:
            self._object_detection.source = '/home/pi/d3-ui/img/object_detection_off.png'
        else:
            self._object_detection.source = '/home/pi/d3-ui/img/object_detection_on.png'

    def _change_exposure(self, instance, val):
        self._camera.set_exposure(int(val))

    def _do_reset_scatter(self, val):
        # move the
        mat = Matrix().scale(10,10,10).translate(0,-150,0)
        self._scatter.transform = mat

    def _auto_change_exposure(self, val):
        # go in steps
        self._auto_centroiding = True
        self._auto_centroid.source = '/home/pi/d3-ui/img/distribution_centroid_on.png'
        t = Thread(name='centroid_thread',
                   target=self._do_auto_change_exposure)
        t.start()

    def _auto_change_exposure_done(self, l):
        # go in steps
        self._auto_centroiding = True
        self._auto_centroid.source = '/home/pi/d3-ui/img/distribution_centroid_off.png'

    # basic pid loop....
    def _do_auto_change_exposure(self):
        epsilon = 1
        previous_error = 0
        integral = 0
        error = 127 - self._histogram.centroid
        dt = 1
        Kp = 0.5
        #Kd = 0.6
        #Ki = 0.6
        Kd = 0.1
        Ki = 0
        tries = 0
        max_tries = 15
        while abs(error) > epsilon and tries < max_tries:
            try:
                integral = integral + error*dt
                derivative = (error - previous_error)/dt
                output = Kp*error + Ki*integral + Kd*derivative + self._camera.get_exposure()
                # set exposure to the output
                if(output < self._exposure_slider.max and output > self._exposure_slider.min):
                    self._camera.set_exposure(int(output))
                    # let the exposure settle
                    sleep(.4)
                previous_error = error
                error = 127 - self._histogram.centroid
                tries += 1
            except:
                e = sys.exc_info()[0]
                Logger.exception('Exception! %s', e)
        Clock.schedule_once(self._auto_change_exposure_done)


    def _exit_app(self, val):
        self._camera.play = False
        # give it a 1/4 sec to shu down the camera
        sleep(0.25)
        App.get_running_app().stop()
        import sys
        sys.exit()

    def _update_histogram(self, val):
        frame = self._camera.get_current_frame()
        self._histogram.set_data(frame)

        #self._histogram.set_pil_image(self._camera.get_current_frame())
        #npImage = np.array(frame)

        #hist_full = cv2.calcHist([npImage],[0],None,[256],[0,256]).ravel()
        #self._plot.points = [(x, hist_full[x]) for x in range(0,256)]


        #plt.plot(hist_full,color = 'b')
        #plt.clf()
        #plt.hist(npImage.ravel(), 256,[0,256])
        #plt.xlim([0,256])
        #self._histogram.draw()


    def _update_fps(self, l):
        self._fps.text = "FPS: %d" % self._camera.get_fps()
        self._exposure.text = "Exposure: %d" % self._camera.get_exposure()
        self._centroid.text = "C: %d" % self._histogram.centroid

        # todo: change this to be event-driven
        if self._camera.is_uploading():
            if self._uploading.pos_hint['pos'][0] < 0:
                self._uploading.pos_hint = {'pos':(0.0,0.9)}
                self._uploadingAmt.pos_hint = {'pos': (0.0, 0.8)}
                self._upload_progress.pos_hint = {'pos':(0.2,0.9)}
                #self._demo.pos_hint = {'pos': (0.0, 0.7)}
                self._snap.enabled = False
            self._upload_progress.value = 100 * self._camera.get_uploaded_size() / self._camera.get_total_upload_size()
            self._uploadingAmt.text = '%d kB' % int(self._camera.get_uploaded_size() / 1000)
        else:
            if self._uploading.pos_hint['pos'][0] >= 0:
                try:
                    self._uploading.pos_hint = {'pos':(-1,-1)}
                    self._upload_progress.pos_hint = {'pos':(-1,-1)}
                    self._uploadingAmt.pos_hint = {'pos': (-1, -1)}
                    self._upload_progress.pos_hint = {'pos':(-1,-1)}

                    #self._demo.pos_hint = {'pos': (-1, -1)}
                    self._snap.enabled = True
                except:
                    e = sys.exc_info()[0]
                    Logger.exception('Exception! %s', e)

    def updateImages(self):
        if not self._is_updating:
            t = Thread(name='image_thread',
                       target=self._do_download)
            t.start()

    def _do_download(self):
        try:
            self._is_updating = True
            local_recon ='/home/pi/recon'

            if not os.path.exists(local_recon):
                os.makedirs(local_recon)

            dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAABGyzVVQi_3q7CkUoPjSjO6tWId31ogOM0KiBcdowZoB0b")
            # dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAAAp3MyYSImy0N0-3IMflqMPenGwEWJPqxAWeOAFzKu6y9A")
            # remote_path = '/input_test/D3RaspberryPi/%s' % os.path.basename(file)
            remote_recon = '/input/D3RaspberryPi/recon/'

            mode = dropbox.files.WriteMode.overwrite
            #mtime = os.path.getmtime(file)

            # list the folder contents
            try:
                res = dbx.files_list_folder(remote_recon)
                for entry in res.entries:
                    local_file = os.path.join(local_recon, entry.name)
                    if not os.path.exists (local_file):
                        # download and overwrite it
                        md, dl_res = dbx.files_download(entry.path_lower)
                        file = open(local_file, 'w')
                        file.write(dl_res.content)
                        file.close
                #delete items no longer in dropbox
                # for localfile in os.listdir(local_recon):
                #     local_file = os.path.join(local_recon, entry.name)
                #     if not os.path.exists (local_file):
                #         # download and overwrite it
                #         md, dl_res = dbx.files_download(local_file)
                #         file = open(local_file, 'w')
                #         file.write(dl_res.content)
                #         file.close
                Clock.schedule_once(self.updateResultsButton, 0.5)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return None
        except:
            e = sys.exc_info()[0]
            Logger.exception('Exception! %s', e)
            Clock.schedule_once(self.updateResultsButton, 0.5)
        self._is_updating = False

    def updateResultsButton(self, dt=None):
        try:
            # todo: contact dropbox
            local_recon = '/home/pi/recon'
            for local_file in os.listdir(local_recon):
                if local_file.endswith('.raw.log.iphone.log'):
                    btn = Button(text=local_file, size_hint_y=None, height=44)
                    btn.bind(on_release=lambda btn: self._show_carousel(btn.text))
                    self._dropdown.add_widget(btn)
        except:
            # do nothing
            print('error')

    def build(self):

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_Pin, GPIO.OUT)
        self._led_state =  GPIO.LOW
        GPIO.output(LED_Pin, self._led_state)

        #layout = BoxLayout(orientation='vertical')
        layout = FloatLayout(size=(800, 480), pos=(0,0))

        self._toggle = ToggleButton(text='LED OFF',
           size_hint=(0.2,0.2), pos_hint={'pos':(0.8,0)})

        self._snap = Button(text='Capture',
           size_hint=(0.2,0.2), pos_hint={'pos':(0.8,0.2)})

        self._snapref = Button(text='Reference',
           size_hint=(0.2,0.2), pos_hint={'pos':(0.8,0.4)})

        self._demo = Button(text='Demo Results',
           size_hint=(0.2,0.1), pos_hint={'pos': (0.0, 0.7)})

        self._auto_centroid = ImageButton(size_hint=(0.1,0.1), pos_hint={'pos':(0.7,0)},
            source='/home/pi/d3-ui/img/distribution_centroid_off.png')

        self._object_detection = ImageButton(size_hint=(0.1,0.1), pos_hint={'pos':(0.7,0.1)},
            source='/home/pi/d3-ui/img/object_detection_off.png')

        self._reset_scatter = ImageButton(size_hint=(0.1,0.1), pos_hint={'pos':(0.7,0.2)},
            source='/home/pi/d3-ui/img/reset_scatter.png')


        self._exit = Button(text='X', size_hint=(0.05,0.05),
                            pos_hint={'pos':(0.95,0.95)})

        self._fps = Label(text='FPS: 0', size_hint=(0.1,0.1),
                          pos_hint={'pos':(0.8,0.9)})
        self._uploading = Label(text='Uploading...', size_hint=(0.2,0.1),
                          pos_hint={'pos':(-1,-1)}, color=[0,0,1,0])
        self._uploadingAmt = Label(text='', size_hint=(0.2,0.1),
                          pos_hint={'pos':(-1,-1)}, color=[0,0,1,0])

        self._exposure = Label(text='Exposure: 0', size_hint=(0.2,0.1),
                          pos_hint={'pos':(0,0)})

        self._centroid = Label(text='C:0', size_hint=(0.1,0.1),
                          pos_hint={'pos':(0.79,0.83)}, color=[1,0,0,1])

        self._exposure_slider = Slider(min=0, max=2500, value=333,
                          size_hint=(0.5,0.1),
                          pos_hint={'pos':(0.2,0)}  )

        self._upload_progress = ProgressBar(max=100, size_hint=(0.5,0.1),
                          pos_hint={'pos':(-1,-1)})

        self._camera = CameraD3(resolution=(640,480),
                                fourcc="GREY",
                                capture_resolution=(3872, 2764),
                                capture_fourcc="Y16 ",
                                size_hint=(1,1),
                                pos_hint={'pos':(0,0)},
                                play=True, )

        self._dropdown = DropDown()

        # create a big main button
        self._imageResultsButton = Button(text='Image Explorer',pos_hint={'pos': (0.0, 0.6)}, size_hint=(0.2, 0.1))

        # show the dropdown menu when the main button is released
        # note: all the bind() calls pass the instance of the caller (here, the
        # mainbutton instance) as the first argument of the callback (here,
        # dropdown.open.).
        self._imageResultsButton.bind(on_release=self._dropdown.open)

        # one last thing, listen for the selection in the dropdown list and
        # assign the data to the button text.
        self._dropdown.bind(on_select=lambda instance, x: setattr(self._imageResultsButton, 'text', x))



        # self._camera = CameraD3(resolution=(1280,720),
        #                         play=True, fourcc="GREY")

        # self._camera = CameraD3(resolution=(3872, 2764),
        #                       play=True, fourcc="Y16 ")

        # self._camera = CameraD3(resolution=(1920,1080),
        #                        play=True, fourcc="GREY")

        # self._camera = CameraD3(resolution=(2560, 1920),
        #                        play=True, fourcc="GREY")

        self._histogram = Histogram(
            size_hint=(0.2,0.3), pos_hint={'pos':(0.8,0.6)})

        self._demo.bind(on_press=self._show_demo_results)
        self._toggle.bind(on_press=self._led_toggle)
        self._snap.bind(on_press=self._request_capture)
        self._snapref.bind(on_press=self._request_ref_capture)
        self._exit.bind(on_press=self._exit_app)
        self._auto_centroid.bind(on_press=self._auto_change_exposure)
        self._object_detection.bind(on_press=self._toggle_object_detection)
        self._exposure_slider.bind(value=self._change_exposure)
        self._reset_scatter.bind(on_press=self._do_reset_scatter)

        #update.bind(on_press=self._update_histogram)
        self._camera.fbind('on_frame_complete',self._update_histogram)

        self._scatter = Scatter(size_hint=(None, None), size=(200,200),)
        self._scatter.add_widget(self._camera)
        #layout.add_widget(self._camera)
        layoutInner = FloatLayout(size_hint=(0.8, 1), pos_hint={'x':0,'y':0})
        layoutInner.add_widget(self._scatter)
        layout.add_widget(layoutInner)

        mat = Matrix().scale(10,10,10).translate(0,-150,0)
        self._scatter.apply_transform(mat)
        layout.add_widget(self._imageResultsButton)
        layout.add_widget(self._uploading)
        layout.add_widget(self._uploadingAmt)
        layout.add_widget(self._demo)
        layout.add_widget(self._histogram)
        layout.add_widget(self._snap)
        layout.add_widget(self._snapref)
        layout.add_widget(self._exit)
        layout.add_widget(self._centroid)
        layout.add_widget(self._exposure_slider)
        layout.add_widget(self._upload_progress)
        layout.add_widget(self._auto_centroid)
        layout.add_widget(self._object_detection)
        layout.add_widget(self._reset_scatter)

        layout.add_widget(self._exposure)
        layout.add_widget(self._fps)
        Clock.schedule_interval(self._update_fps, 2)
        layout.add_widget(self._toggle)
        #layout.add_widget(update)

        self._is_updating = False
        self.updateImages()
        return layout

TestCamera().run()

