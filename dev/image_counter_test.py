from PIL import Image, ImageDraw, ImageFont
# get an image
base = Image.open('D:/Sextus share/temp1.jpg').convert('RGBA')

# make a blank image for the text, initialized to transparent text color
txt = Image.new('RGBA', base.size, (255,255,255,0))

# get a font
fnt = ImageFont.truetype('garamond8.ttf', base.size[0] // 10)

# get a drawing context
d = ImageDraw.Draw(txt)

string = '2'
textsize = d.textsize(string, font=fnt)

# draw text, full opacity
draw_position = (base.size[0] / 2, int(base.size[1] * 0.9))
circle_radius = max(textsize) // 2
circle_bounds = [(draw_position[0] - circle_radius, draw_position[1] - circle_radius),
	(draw_position[0] + circle_radius, draw_position[1] + circle_radius)]
text_position = (draw_position[0] - textsize[0]/2, draw_position[1] - textsize[1]//1.5)
d.ellipse(circle_bounds, fill=(255,255,255,64))
#d.ellipse([(draw_position[0] - 5, draw_position[1] - 5), (draw_position[0] + 5, draw_position[1] + 5)], fill=(255,0,0,128))
#d.ellipse([(text_position[0] - 5, text_position[1] - 5), (text_position[0] + 5, text_position[1] + 5)], fill=(0,255,0,128))
d.text(text_position, string, font=fnt, fill=(64,64,64,255))
print 'draw_position;', draw_position
print 'text_position:', text_position
print 'fontsize:', base.size[0] // 10
print 'base.size:', base.size
print 'textsize:', textsize
print 'circle_radius:', circle_radius

out = Image.alpha_composite(base, txt)

out.show()

#base.save('D:/Sextus share/test2.jpg', 'jpeg')