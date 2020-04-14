import sys
import os

from PIL import Image

BUTTERFLIES = 9
SPRITES = 10

SPRITE_WIDTH = 64
SPRITE_HEIGHT = 32

SS_WIDTH = SPRITE_WIDTH * SPRITES * 2 # cause they're mirrored
SS_HEIGHT = SPRITE_HEIGHT * BUTTERFLIES

CROP_X = 235
CROP_Y = 215
CROP_WIDTH = 128
CROP_HEIGHT = 64

# Setting the points for cropped image 
left = CROP_X
top = CROP_Y
right = CROP_X + CROP_WIDTH
bottom = CROP_Y + CROP_HEIGHT

butterfly_folder = 'art/butterfly'

def main():
    canvas = Image.new('RGBA', (SS_WIDTH, SS_HEIGHT), (255, 0, 0, 0))

    
    for i in range(0, BUTTERFLIES):
        for j in range(0, SPRITES):
            filename = os.path.join(butterfly_folder, f"0{i+1}/{names[i]}000{j}.png")
            print(filename)
            im = Image.open(filename)
            im1 = im.crop((left, top, right, bottom))
            newsize = (64,32)
            im1 = im1.resize(newsize)
            offset = (j*SPRITE_WIDTH*2, i*SPRITE_HEIGHT)
            canvas.paste(im1, offset)
            im2 = im1.transpose(Image.FLIP_LEFT_RIGHT)
            offset2 = (j*SPRITE_WIDTH*2+SPRITE_WIDTH, i*SPRITE_HEIGHT)
            canvas.paste(im2, offset2)
    
    #canvas.show()
    canvas.save('assets/sprites/butterflies.png')

names = [
    'butterfly',
    'G2Butterfly',
    'G3Butterfly',
    'G4Butterfly',
    'G5Butterfly',
    'G6Butterfly',
    'G7Butterfly',
    'G8Butterfly',
    'G9Butterfly'
]

if __name__ == "__main__":
    main()
