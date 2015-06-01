from __future__ import absolute_import

from willow.states import (
    ImageState,
    JPEGImageFileState,
    PNGImageFileState,
    GIFImageFileState,
    RGBImageBufferState,
    RGBAImageBufferState,
)


def _PIL_Image():
    import PIL.Image
    return PIL.Image


class PillowImageState(ImageState):
    def __init__(self, image):
        self.image = image

    @classmethod
    def check(cls):
        _PIL_Image()

    @ImageState.operation
    def get_size(self):
        return self.image.size

    @ImageState.operation
    def has_alpha(self):
        img = self.image
        return img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)

    @ImageState.operation
    def has_animation(self):
        # Animation is not supported by PIL
        return False

    @ImageState.operation
    def resize(self, size):
        if self.image.mode in ['1', 'P']:
            image = self.image.convert('RGB')
        else:
            image = self.image

        image = image.resize(size, _PIL_Image().ANTIALIAS)

        return PillowImageState(image)

    @ImageState.operation
    def crop(self, rect):
        return PillowImageState(self.image.crop(rect))

    @ImageState.operation
    def save_as_jpeg(self, f, quality=85):
        if self.image.mode in ['1', 'P']:
            image = self.image.convert('RGB')
        else:
            image = self.image

        image.save(f, 'JPEG', quality=quality)

    @ImageState.operation
    def save_as_png(self, f):
        self.image.save(f, 'PNG')

    @ImageState.operation
    def save_as_gif(self, f):
        if 'transparency' in self.image.info:
            self.image.save(f, 'GIF', transparency=self.image.info['transparency'])
        else:
            self.image.save(f, 'GIF')

    @classmethod
    @ImageState.converter_from(JPEGImageFileState)
    @ImageState.converter_from(PNGImageFileState)
    @ImageState.converter_from(GIFImageFileState)
    def open(cls, state):
        state.f.seek(0)
        image = _PIL_Image().open(state.f)
        image.load()

        # JPEG files can be orientated using an EXIF tag.
        # Make sure this orientation is applied to the data
        if isinstance(state, JPEGImageFileState):
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    # 0x0112 = Orientation
                    orientation = exif.get(0x0112, 1)

                    Image = _PIL_Image()
                    ORIENTATION_TO_TRANSPOSE = {
                        1: (),
                        2: (Image.FLIP_LEFT_RIGHT,),
                        3: (Image.ROTATE_180,),
                        4: (Image.ROTATE_180, Image.FLIP_LEFT_RIGHT),
                        5: (Image.ROTATE_270, Image.FLIP_LEFT_RIGHT),
                        6: (Image.ROTATE_270,),
                        7: (Image.ROTATE_90, Image.FLIP_LEFT_RIGHT),
                        8: (Image.ROTATE_90,),
                    }

                    for transpose in ORIENTATION_TO_TRANSPOSE[orientation]:
                        image = image.transpose(transpose)

        return cls(image)

    @ImageState.converter_to(RGBImageBufferState)
    def to_buffer_rgb(self):
        image = self.image

        if image.mode != 'RGB':
            image = image.convert('RGB')

        return RGBImageBufferState(image.size, image.tobytes())

    @ImageState.converter_to(RGBAImageBufferState)
    def to_buffer_rgba(self):
        image = self.image

        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        return RGBAImageBufferState(image.size, image.tobytes())


willow_state_classes = [PillowImageState]
