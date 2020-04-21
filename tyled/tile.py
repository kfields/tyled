from PIL import Image

class Tile:
    def __init__(self, source, id, kind):
        self.source = source
        self.id = id
        self.type = kind

        self.image = image = Image.open(source)
        self.position = (0,0)
        self.width, self.height = image.size
        self.angle = None

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    def __repr__(self):
        return f"<Tile src={self.source} x={self.x} y={self.y} width={self.width} height={self.height}>"

    def place(self, position, angle=None):
        self.position = position
        self.angle = angle

    def draw(self, canvas, position, angle=None):
        self.position = position
        self.angle = angle if angle else 0

        im = self.image
        if angle:
            im = self.image.rotate(angle, expand=True)
        canvas.paste(im, position)
