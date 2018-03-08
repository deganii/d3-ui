from kivy.uix.image import Image
from core_camera_d3 import CoreCameraD3 as CoreCamera
from kivy.properties import NumericProperty, ListProperty, \
    BooleanProperty, StringProperty


class CameraD3(Image):
    '''Camera class. See module documentation for more information.
    '''

    play = BooleanProperty(True)
    '''Boolean indicating whether the camera is playing or not.
    You can start/stop the camera by setting this property::
        # start the camera playing at creation (default)
        cam = Camera(play=True)
        # create the camera, and start later
        cam = Camera(play=False)
        # and later
        cam.play = True
    :attr:`play` is a :class:`~kivy.properties.BooleanProperty` and defaults to
    True.
    '''

    index = NumericProperty(-1)
    '''Index of the used camera, starting from 0.
    :attr:`index` is a :class:`~kivy.properties.NumericProperty` and defaults
    to -1 to allow auto selection.
    '''

    resolution = ListProperty([-1, -1])
    '''Preferred resolution to use when invoking the camera. If you are using
    [-1, -1], the resolution will be the default one::
        # create a camera object with the best image available
        cam = Camera()
        # create a camera object with an image of 320x240 if possible
        cam = Camera(resolution=(320, 240))
    .. warning::
        Depending on the implementation, the camera may not respect this
        property.
    :attr:`resolution` is a :class:`~kivy.properties.ListProperty` and defaults
    to [-1, -1].
    '''


    capture_resolution = ListProperty([-1, -1])
    capture_fourcc = StringProperty()

    def __init__(self, **kwargs):
        self._camera = None
        super(CameraD3, self).__init__(**kwargs)
        if self.index == -1:
            self.index = 0
        on_index = self._on_index
        fbind = self.fbind
        fbind('index', on_index)
        fbind('resolution', on_index)
        self.register_event_type('on_frame_complete')
        on_index()

    def on_tex(self, *l):
        self.canvas.ask_update()
        self.dispatch('on_frame_complete')

    #def on_capture_complete(self, *1):


    def _on_index(self, *largs):
        self._camera = None
        if self.index < 0:
            return
        if self.resolution[0] < 0 or self.resolution[1] < 0:
            return
        self._camera = CoreCamera(index=self.index,
                                  resolution=self.resolution, stopped=True,
                                  capture_resolution = self.capture_resolution,
                                    capture_fourcc = self.capture_fourcc)
        self._camera.bind(on_load=self._camera_loaded)
        self._camera.bind(on_texture=self.on_tex)

        if self.play:
            self._camera.start()

    def get_current_frame(self):
        return self._camera.get_current_frame()

    def get_fps(self):
        return self._camera.get_fps()

    def set_exposure(self, val):
        return self._camera.set_exposure(val)

    def get_exposure(self):
        return self._camera.get_exposure()

    def get_uploaded_size(self):
        return self._camera.get_uploaded_size()

    def get_total_upload_size(self):
        return self._camera.get_total_upload_size()

    def set_object_detection(self, val):
        self._camera._object_detection = val

    def get_object_detection(self):
        return self._camera.get_object_detection()

    def is_uploading(self):
        return self._camera.is_uploading()

    def _camera_loaded(self, *largs):
        self.texture = self._camera.texture
        self.texture_size = list(self.texture.size)

    def on_play(self, instance, value):
        if not self._camera:
            return
        if value:
            self._camera.start()
        else:
            self._camera.stop()

    def capture__full_res_frame(self, *largs):
        return self._camera.capture__full_res_frame()

    def capture__full_res_ref(self, *largs):
        return self._camera.capture__full_res_ref()

    def on_frame_complete(self, *args):
        pass