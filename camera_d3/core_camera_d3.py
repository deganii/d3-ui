from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.core.camera import CameraBase
import select
import v4l2capture
from PIL import Image
from threading import Thread
from kivy.logger import Logger
import sys
from time import sleep
import time
import datetime
import numpy as np

# dropbox related (todo: move into separate class)
import os
import dropbox
from io import BytesIO

# overlay related (todo: move into separate class)
import cv2
import cv2.cv as cv
import numpy as np

class CoreCameraD3(CameraBase):
    """Implementation of ImagingSource Camera for D3
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('fourcc', 'GRAY')
        # kwargs.setdefault('mode', 'L')
        self._user_buffer = None
        self._format = 'rgb'
        self._video_src = 'v4l'
        self._device = None
        self._texture_size = None
        self._fourcc = kwargs.get('fourcc')
        self._mode = kwargs.get('mode')
        self._capture_resolution = kwargs.get('capture_resolution')
        self._capture_fourcc = kwargs.get('capture_fourcc')
        self.capture_requested = False
        self.ref_requested = False
        self._exposure_requested = False
        self._requested_exposure = 0
        self._exposure = 0
        self._uploading = False
        self._uploaded_size = 0
        self._total_upload_size = 0
        self._object_detection = False
        self._fps = 0
        if self._mode is None:
            self._mode = self._get_mode_from_fourcc(self._fourcc)

        super(CoreCameraD3, self).__init__(**kwargs)

    def _get_mode_from_fourcc(self, fourcc):
            return "I;16" if fourcc == "Y16 " else "L"

    def init_camera(self):
        self._device = '/dev/video%d' % self._index
        if not self.stopped:
            self.start()

    def is_uploading(self):
        return self._uploading

    def upload(self, file):
        self._uploading = True
        t = Thread(name='dropbox_thread',
                   target=self._do_upload_chunked, args=(file,))
        t.start()



    def _do_upload_chunked(self, file):
        try:
            CHUNK_SIZE = 1024*256
            self._total_upload_size = os.path.getsize(file)
            self._uploaded_size = 0
            upload_id = None
            dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAABGyzVVQi_3q7CkUoPjSjO6tWId31ogOM0KiBcdowZoB0b")
            # old app-only access
            # dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAAAp3MyYSImy0N0-3IMflqMPenGwEWJPqxAWeOAFzKu6y9A")
            #remote_path = '/input_test/D3RaspberryPi/%s' % os.path.basename(file)
            remote_path = '/input/D3RaspberryPi/%s' % os.path.basename(file)
            mode = dropbox.files.WriteMode.overwrite
            mtime = os.path.getmtime(file)
            with open(file, 'rb') as f:
                if self._total_upload_size <= CHUNK_SIZE:
                    dbx.files_upload(f.read(), remote_path, mode,
                        client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                        mute=True)
                else:
                    try:
                        upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                        cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                               offset=f.tell())
                        commit = dropbox.files.CommitInfo(path=remote_path)

                        while f.tell() < self._total_upload_size:
                            if ((self._total_upload_size - f.tell()) <= CHUNK_SIZE):
                                dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                                self._uploaded_size = self._total_upload_size
                            else:
                                dbx.files_upload_session_append(f.read(CHUNK_SIZE), cursor.session_id,  cursor.offset)
                                self._uploaded_size = cursor.offset = f.tell()
                    except dropbox.exceptions.ApiError as err:
                        print('*** API error', err)
        except:
            e = sys.exc_info()[0]
            Logger.exception('Exception! %s', e)
        self._uploading = False

    def _doupload(self, file):
        try:
            dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAABGyzVVQi_3q7CkUoPjSjO6tWId31ogOM0KiBcdowZoB0b")
            #dbx = dropbox.Dropbox("Yk7MLEza3NAAAAAAAAAAp3MyYSImy0N0-3IMflqMPenGwEWJPqxAWeOAFzKu6y9A")
            # remote_path = '/input_test/D3RaspberryPi/%s' % os.path.basename(file)
            path = '/input/D3RaspberryPi/%s' % os.path.basename(file)
            mode = dropbox.files.WriteMode.overwrite
            mtime = os.path.getmtime(file)
            with open(file, 'rb') as f:
                data = f.read()
            #with stopwatch('upload %d bytes' % len(data)):
            try:
                res = dbx.files_upload(data, path, mode,
                    client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                    mute=True)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return None
            print('uploaded as', res.name.encode('utf8'))
        except:
            e = sys.exc_info()[0]
            Logger.exception('Exception! %s', e)
        self._uploading = False

    def _do_capture(self, is_ref):
        try:
            device = self._device
            video = v4l2capture.Video_device(device)
            (res_x, res_y) = self._capture_resolution
            fourcc = self._capture_fourcc
            (size_x, size_y) = video.set_format(res_x, res_y, fourcc=fourcc)
            capture_texture_size = (size_x, size_y)
            video.create_buffers(1)
            video.queue_all_buffers()
            video.start()
            select.select((video,), (), ())
            image_data = video.read_and_queue()
            Logger.debug("Obtained a frame of size %d", len(image_data))
            image = Image.frombytes(self._get_mode_from_fourcc(fourcc),
                                    capture_texture_size, image_data)
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%Hh-%Mm-%Ss')
            if is_ref:
                file = '/home/pi/d3-captures/reference-%s.tiff' % st
            else:
                file = '/home/pi/d3-captures/capture-%s.tiff' % st
            image.save(file, format='TIFF')

            #self._user_buffer = image
            #Clock.schedule_once(self._capture_complete)
            video.close()

            # start the dropbox upload
            # todo: move this out of the camera code!
            self.upload(file)
        except:
            e = sys.exc_info()[0]
            Logger.exception('Exception! %s', e)
            Clock.schedule_once(self.stop)

    def _v4l_init_video(self):
        device = self._device
        (res_x, res_y) = self.resolution
        fourcc = self._fourcc
        Logger.info("video_thread started")
        video = v4l2capture.Video_device(device)
        (size_x, size_y) = video.set_format(res_x, res_y, fourcc=fourcc)
        self._texture_size = (size_x, size_y)
        Logger.info("Received resolution: %d,%d", size_x, size_y)
        video.create_buffers(1)
        video.queue_all_buffers()
        video.start()
        self._reset_fps()
        return video

    def _v4l_loop(self):
        while True:
            try:
                video = self._v4l_init_video()
                # set to the auto on startup
                # video.set_exposure_absolute(400)
            except:
                e = sys.exc_info()[0]
                Logger.exception('Exception on video thread startup! %s', e)
                try:
                    if video is not None:
                        video.close()
                except:
                    e2 = sys.exc_info()[0]
                    Logger.info("Exception while trying to close video stream for retry... %s", e2)
                Logger.info("Trying to restart video stream")
                # Try again in a second...
                sleep(2.0)
            break # get out of the loop once this works...

        while not self.stopped:
            try:

                # Logger.debug("Obtaining a frame...")
                select.select((video,), (), ())
                image_data = video.read_and_queue()
                # Logger.debug("Obtained a frame of size %d", len(image_data))
                image = Image.frombytes(self._mode, self._texture_size, image_data)
                self._user_buffer = image

                # convert to rgb for display on-screen
                while (self._buffer is not None):
                    # make this an event object?
                    sleep(0.02)



                #self._buffer = image.convert('RGB').tobytes("raw", "RGB")
                image = image.convert('RGB')

                # draw some hough circles on the RGB buffer as an overlay
                if self._object_detection:
                    # convert from PIL RGB colorspace to opencv's BGR
                    color_imcv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
                    gray_imcv = np.asarray(self._user_buffer)
                    circles = cv2.HoughCircles(gray_imcv, cv.CV_HOUGH_GRADIENT, 1, 2, np.array([]), 100, 10,0,10)
                    if circles is not None:
                        a, b, c = circles.shape
                        for i in range(b):
                                cv2.circle(color_imcv, (circles[0][i][0], circles[0][i][1]), circles[0][i][2], (0, 0, 255), 3, cv2.CV_AA)
                                cv2.circle(color_imcv, (circles[0][i][0], circles[0][i][1]), 2, (0, 255, 0), 3, cv2.CV_AA)  # draw center of circle
                        # convert back from opencv's BGR colorspace to PIL RGB
                        image = Image.fromarray(cv2.cvtColor(color_imcv,cv2.COLOR_BGR2RGB))

                # convert to RGB in order to display on-screen
                self._buffer = image.tobytes("raw", "RGB")
                self._fps_tick()

                Clock.schedule_once(self._update)

                self._exposure = video.get_exposure_absolute()

                if(self._exposure_requested):
                    video.set_exposure_absolute(self._requested_exposure)
                    self._exposure_requested = False

                if(self.capture_requested or self.ref_requested):
                    # need to switch to high res mode
                    video.close()
                    self._do_capture(self.ref_requested)
                    self.capture_requested = False
                    self.ref_requested = False
                    # reinitialize
                    video = self._v4l_init_video()
            except:
                e = sys.exc_info()[0]
                Logger.exception('Exception! %s', e)
                video.close()
                Logger.info("Trying to restart video stream")
                # Try again...
                sleep(1.0)
                video = self._v4l_init_video()

                #Clock.schedule_once(self.stop)
        Logger.info("closing video object")
        video.close()
        Logger.info("video_thread exiting")

    def _reset_fps(self):
        self.TICK_SAMPLES = 25
        self._ticksum = 0
        self._tickindex = 0
        self._tick_samples = np.zeros(self.TICK_SAMPLES)
        self._lasttime = time.time()
        self._fps = 0

    def _fps_tick(self):
        newtime = time.time()
        newtick = newtime - self._lasttime
        self._ticksum -= self._tick_samples[self._tickindex]
        self._ticksum += newtick
        self._tick_samples[self._tickindex] = newtick
        self._tickindex = (self._tickindex + 1) % self.TICK_SAMPLES
        self._fps = self.TICK_SAMPLES / self._ticksum
        self._lasttime = newtime

    def start(self):
        Logger.info("d3 camera start() called")
        super(CoreCameraD3, self).start()
        t = Thread(name='video_thread',
                   target=self._v4l_loop)
        t.start()

    def stop(self, dt=None):
        super(CoreCameraD3, self).stop()

    def get_current_frame(self):
        return self._user_buffer

    def capture__full_res_frame(self):
        self.capture_requested = True

    def capture__full_res_ref(self):
        self.ref_requested = True

    def get_fps(self):
        return self._fps

    def set_exposure(self, val):
        self._requested_exposure = val
        self._exposure_requested = True

    def get_exposure(self):
        return self._exposure

    def get_total_upload_size(self):
        return self._total_upload_size

    def get_uploaded_size(self):
        return self._uploaded_size

    def set_object_detection(self, val):
        self._object_detection = val

    def get_object_detection(self):
        return self._object_detection

    def _update(self, dt):
        if self._buffer is None:
            return
        Logger.debug("Rendering a frame...")
        if self._texture is None and self._texture_size is not None:
            Logger.debug("Creating a new texture...")
            self._texture = Texture.create(
                size=self._texture_size, colorfmt='rgb')
            self._texture.flip_vertical()
            self.dispatch('on_load')
        self._copy_to_gpu()

    #def _capture_complete(self):
    #    self.dispatch('on_capture_complete')

    def on_texture(self):
        pass

    def on_load(self):
        pass

