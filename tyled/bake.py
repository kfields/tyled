import sys
import os
import glob

from PIL import Image

def main(ts):
    source = ts.source
    name = ts.name
    tilewidth = ts.tilewidth
    tileheight = ts.tileheight
    spacing = ts.spacing
    margin = ts.margin
    columns = ts.columns

    tilecount = ts.tilecount
    width = ts.width

    files = ts.files
    tilecount = ts.tilecount
    rows = ts.rows
    height = ts.height

    canvas = Image.new('RGBA', (width, height), (255, 0, 0, 0))

    
    for i in range(0, columns):
        for j in range(0, rows):
            filename = files.pop(0)
            print(filename)
            
            im = Image.open(filename)
            im1 = im
            #offset = ( margin + (j*(tilewidth+(spacing*2))), margin + (i*(tileheight+(spacing*2))) )
            offset = ( margin + (j*(tilewidth+(spacing))), margin + (i*(tileheight+(spacing))) )
            canvas.paste(im1, offset)
            
    #canvas.show()
    canvas.save(f"{name}.png")

'''
def main(config):
    print(config)
    firstgid = config["firstgid"]
    source = config["source"]
    name = config["name"]
    tilewidth = config["tilewidth"]
    tileheight = config["tileheight"]
    spacing = config["spacing"]
    margin = config["margin"]
    columns = config["columns"]

    tilecount = 0
    ts_width = (margin*2) + columns * (tilewidth+(spacing*2))

    files = sorted(glob.glob(f"{source}/*.png"))
    file_count = len(files)
    rows = int(file_count / columns)
    ts_height = (margin*2) + rows * (tileheight+(spacing*2))

    canvas = Image.new('RGBA', (ts_width, ts_height), (255, 0, 0, 0))

    
    for i in range(0, columns):
        for j in range(0, rows):
            #filename = os.path.join(butterfly_folder, f"0{i+1}/{names[i]}000{j}.png")
            filename = files.pop(0)
            print(filename)
            
            im = Image.open(filename)
            im1 = im
            #im1 = im.crop((left, top, right, bottom))
            #newsize = (64,32)
            #im1 = im1.resize(newsize)
            offset = ( margin + (j*(tilewidth+(spacing*2))), margin + (i*(tileheight+(spacing*2))) )
            #offset = (j*tilewidth*2, i*tileheight)
            canvas.paste(im1, offset)
            #im2 = im1.transpose(Image.FLIP_LEFT_RIGHT)
            #offset2 = (j*SPRITE_WIDTH*2+SPRITE_WIDTH, i*SPRITE_HEIGHT)
            #canvas.paste(im2, offset2)
            
    #canvas.show()
    canvas.save(f"{name}.png")
'''
if __name__ == "__main__":
    main()
