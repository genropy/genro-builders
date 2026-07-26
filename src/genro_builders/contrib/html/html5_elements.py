# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML5 element definitions for HtmlBuilder.

Originally derived (April 2026) from the W3C HTML5 Validator
RELAX NG schema. From now on it is **hand-maintained**: edits and
additions go in directly. The schema-diff utility in
``importer/html5_schema_builder.py`` exists to spot W3C drift on
demand, not to regenerate this file.
"""

from __future__ import annotations

from genro_builders.builder import element


class Html5Elements:
    """HTML5 element mixin. Provides @element for all HTML5 tags."""

    @element(sub_tags="*")
    def a(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def abbr(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def address(self, **kwargs): ...

    @element()
    def area(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def article(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def aside(self, **kwargs): ...

    @element(sub_tags="*")
    def audio(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def b(self, **kwargs): ...

    @element()
    def base(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def bdi(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def bdo(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def blockquote(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
        node_label='body',
    )
    def body(self, **kwargs): ...

    @element()
    def br(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def button(self, **kwargs): ...

    @element(sub_tags="*")
    def canvas(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def caption(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def cite(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def code(self, **kwargs): ...

    @element()
    def col(self, **kwargs): ...

    @element(sub_tags='col,script,template')
    def colgroup(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def data(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,option,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def datalist(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dd(self, **kwargs): ...

    @element(sub_tags="*")
    def del_(self, **kwargs): ...  # transparent content ('del' is a Python keyword)

    @element(sub_tags='summary')
    def details(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def dfn(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dialog(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def div(self, **kwargs): ...

    @element(sub_tags='div,dt,script,template')
    def dl(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dt(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def em(self, **kwargs): ...

    @element()
    def embed(self, **kwargs): ...

    @element(sub_tags='legend')
    def fieldset(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def figcaption(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figcaption,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def figure(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def footer(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def form(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h1(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h2(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h3(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h4(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h5(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h6(self, **kwargs): ...

    @element(
        sub_tags='base,link,meta,noscript,script,style,template,title',
        node_label='head',
    )
    def head(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def header(self, **kwargs): ...

    @element(sub_tags='h1,h2,h3,h4,h5,h6,p,script,template')
    def hgroup(self, **kwargs): ...

    @element()
    def hr(self, **kwargs): ...

    @element(sub_tags='head,body')
    def html(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def i(self, **kwargs): ...

    @element()
    def iframe(self, **kwargs): ...

    @element()
    def img(self, **kwargs): ...

    @element()
    def input(self, **kwargs): ...

    @element(sub_tags="*")
    def ins(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def kbd(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def label(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,h1,h2,h3,h4,h5,h6,hgroup,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def legend(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def li(self, **kwargs): ...

    @element()
    def link(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def main(self, **kwargs): ...

    @element(sub_tags="*")
    def map(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def mark(self, **kwargs): ...

    @element(sub_tags='li,script,template')
    def menu(self, **kwargs): ...

    @element()
    def meta(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def meter(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def nav(self, **kwargs): ...

    @element(sub_tags="*")
    def noscript(self, **kwargs): ...  # transparent content

    @element(sub_tags="*")
    def object(self, **kwargs): ...  # transparent content

    @element(sub_tags='li,script,template')
    def ol(self, **kwargs): ...

    @element(sub_tags='div,legend,noscript,option,script,template')
    def optgroup(self, **kwargs): ...

    @element(sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,div,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr')
    def option(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def output(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def p(self, **kwargs): ...

    @element(sub_tags='img,script,source,template')
    def picture(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def pre(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def progress(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def q(self, **kwargs): ...

    @element()
    def rp(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def rt(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def ruby(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def s(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def samp(self, **kwargs): ...

    @element()
    def script(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def search(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def section(self, **kwargs): ...

    @element(sub_tags='button,div,hr,noscript,optgroup,option,script,template')
    def select(self, **kwargs): ...

    @element(sub_tags="*")
    def slot(self, **kwargs): ...  # transparent content

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def small(self, **kwargs): ...

    @element()
    def source(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def span(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def strong(self, **kwargs): ...

    @element()
    def style(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def sub(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,h1,h2,h3,h4,h5,h6,hgroup,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def summary(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def sup(self, **kwargs): ...

    @element(sub_tags='caption,colgroup,script,tbody,template,tfoot,thead,tr')
    def table(self, **kwargs): ...

    @element(sub_tags='script,template,tr')
    def tbody(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def td(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,caption,cite,code,col,colgroup,data,datalist,del_,details,dfn,dialog,div,dl,dt,em,embed,fieldset,figcaption,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,legend,li,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,optgroup,option,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,source,span,strong,style,sub,summary,sup,table,tbody,td,template,textarea,tfoot,th,thead,time,tr,track,u,ul,var,video,wbr',
    )
    def template(self, **kwargs): ...

    @element()
    def textarea(self, **kwargs): ...

    @element(sub_tags='script,template,tr')
    def tfoot(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del_,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,selectedcontent,slot,small,span,strong,style,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def th(self, **kwargs): ...

    @element(sub_tags='script,template,tr')
    def thead(self, **kwargs): ...

    @element()
    def time(self, **kwargs): ...

    @element()
    def title(self, **kwargs): ...

    @element(sub_tags='script,td,template,th')
    def tr(self, **kwargs): ...

    @element()
    def track(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def u(self, **kwargs): ...

    @element(sub_tags='li,script,template')
    def ul(self, **kwargs): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del_,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,selectedcontent,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def var(self, **kwargs): ...

    @element(sub_tags="*")
    def video(self, **kwargs): ...  # transparent content

    @element()
    def wbr(self, **kwargs): ...

    @element(sub_tags='')
    def selectedcontent(self, **kwargs):
        """Mirror of the selected option for Customizable Select (HTML 2024)."""
        ...

