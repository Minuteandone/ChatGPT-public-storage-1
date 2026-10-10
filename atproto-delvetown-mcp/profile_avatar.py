"""Generate FwogBot's green frog avatar entirely inside the trusted server."""
from PIL import Image, ImageDraw
from io import BytesIO

def avatar_png():
    S=512
    im=Image.new("RGB",(S,S),"#15283b")
    d=ImageDraw.Draw(im)
    for y in range(S):
        f=y/S
        d.line([(0,y),(S,y)],fill=(int(23+22*f),int(42+14*f),int(72-15*f)))
    for x,y,r in ((52,155,90),(472,112,104),(390,375,105),(65,411,95)):
        d.ellipse((x-r,y-r,x+r,y+r),fill="#233d3b")
        d.ellipse((x-r//2,y-r//2,x+r//2,y+r//2),fill="#31574b")
    d.ellipse((21,391,491,590),fill="#2b5a64")
    d.ellipse((86,412,437,526),fill="#426f68")
    for x,y,r in ((85,82,6),(443,74,7),(371,140,4),(60,288,3),(469,305,6),(284,44,4)):
        d.ellipse((x-r,y-r,x+r,y+r),fill="#fff0a5")
        d.ellipse((x-2,y-2,x+2,y+2),fill="#fffdea")
    d.ellipse((88,327,425,630),fill="#74adb0",outline="#223e47",width=10)
    d.rounded_rectangle((122,359,388,543),radius=77,fill="#a5d2c3",outline="#213d44",width=8)
    d.ellipse((101,125,250,289),fill="#79c766",outline="#355e43",width=12)
    d.ellipse((270,125,419,289),fill="#79c766",outline="#355e43",width=12)
    d.ellipse((80,171,431,438),fill="#7fd175",outline="#35694e",width=12)
    d.ellipse((127,300,387,439),fill="#c8dfaa")
    for x in (175,332):
        d.ellipse((x-55,179,x+55,289),fill="#367354")
        d.ellipse((x-49,183,x+49,281),fill="#152e42")
        d.ellipse((x-41,196,x+39,273),fill="#0d2036")
        d.ellipse((x-24,194,x-4,216),fill="#ffffff")
        d.ellipse((x+13,246,x+24,257),fill="#92cad9")
    for x in (127,367):
        d.ellipse((x-30,302,x+30,326),fill="#edaa8b")
    for x,y in ((244,291),(269,291),(249,306),(274,306)):
        d.ellipse((x-3,y-3,x+3,y+3),fill="#578f5d")
    d.arc((233,327,288,346),start=3,end=176,fill="#275345",width=5)
    d.rounded_rectangle((180,391,333,479),radius=13,fill="#223e56",outline="#13293b",width=5)
    d.ellipse((243,415,271,443),fill="#91d3a8")
    d.ellipse((229,418,257,434),fill="#91d3a8")
    d.line((257,422,257,447),fill="#c4edbf",width=3)
    d.rounded_rectangle((170,475,341,492),radius=9,fill="#142d40")
    d.ellipse((129,416,198,468),fill="#8dcc79",outline="#35694e",width=5)
    d.ellipse((313,416,380,468),fill="#8dcc79",outline="#35694e",width=5)
    b=BytesIO()
    im.save(b,format="PNG",optimize=True)
    return b.getvalue()
