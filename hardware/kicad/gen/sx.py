import re
def block_at(s,i):
    d=0; j=i
    while True:
        c=s[j]
        if c=='(': d+=1
        elif c==')':
            d-=1
            if d==0: return s[i:j+1]
        elif c=='"':
            j+=1
            while s[j]!='"':
                if s[j]=='\\': j+=1
                j+=1
        j+=1
def get_symbol(path,name):
    s=open(path).read()
    m=re.search(r'\n\t\(symbol "'+re.escape(name)+'"',s)
    return block_at(s,m.start()+2)
def pins(blk):
    out=[]
    for m in re.finditer(r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([\d.]+)\).*?\(name "([^"]*)".*?\(number "([^"]*)"',blk,re.S):
        t,sh,x,y,a,l,n,num=m.groups(); out.append(dict(type=t,x=float(x),y=float(y),a=int(float(a)),len=float(l),name=n,num=num))
    return out
