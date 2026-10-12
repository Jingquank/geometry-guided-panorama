// Deterministic, single-center equirectangular guide renderer. C++17, no libraries.
// Linear Lambertian colors + ambient fill + hard directional shadows, not PBR.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

constexpr double PI = 3.14159265358979323846;
constexpr double EPS = 1e-6;
struct V {
    double x = 0, y = 0, z = 0;
    double operator[](int i) const { return i == 0 ? x : (i == 1 ? y : z); }
    V operator+(const V& b) const { return {x+b.x,y+b.y,z+b.z}; }
    V operator-(const V& b) const { return {x-b.x,y-b.y,z-b.z}; }
    V operator*(double s) const { return {x*s,y*s,z*s}; }
};
double dot(V a,V b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
V cross(V a,V b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
V unit(V v) { return v*(1.0/std::sqrt(dot(v,v))); }
V mn(V a,V b) { return {std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)}; }
V mx(V a,V b) { return {std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)}; }
V readv(std::istream& in) { V v; in>>v.x>>v.y>>v.z; return v; }
struct Triangle { V a,b,c,rgb,normal,lo,hi,center; int id; };
struct Node { V lo,hi; int left=-1,right=-1,start=0,count=0; };
struct Hit { double t=std::numeric_limits<double>::infinity(); int tri=-1; };

class BVH {
public:
    std::vector<Triangle> ts;
    std::vector<int> order;
    std::vector<Node> nodes;
    explicit BVH(std::vector<Triangle> input):ts(std::move(input)) {
        order.resize(ts.size()); std::iota(order.begin(),order.end(),0);
        if(!ts.empty()) build(0,static_cast<int>(ts.size()));
    }
    int build(int start,int end) {
        const double inf=std::numeric_limits<double>::infinity();
        Node n; n.lo={inf,inf,inf}; n.hi={-inf,-inf,-inf};
        V clo=n.lo,chi=n.hi;
        for(int i=start;i<end;i++) { const auto& t=ts[order[i]];
            n.lo=mn(n.lo,t.lo); n.hi=mx(n.hi,t.hi); clo=mn(clo,t.center); chi=mx(chi,t.center); }
        int index=static_cast<int>(nodes.size()); nodes.push_back(n);
        if(end-start<=6) { nodes[index].start=start; nodes[index].count=end-start; return index; }
        V ext=chi-clo; int axis=ext.y>ext.x?1:0; if(ext.z>ext[axis]) axis=2;
        int mid=(start+end)/2;
        std::nth_element(order.begin()+start,order.begin()+mid,order.begin()+end,
            [&](int a,int b) { return ts[a].center[axis]<ts[b].center[axis]; });
        int left=build(start,mid),right=build(mid,end);
        nodes[index].left=left; nodes[index].right=right; return index;
    }
    bool box_hit(const Node& n,V o,V d,double limit) const {
        double near=EPS,far=limit;
        for(int axis=0;axis<3;axis++) {
            if(std::abs(d[axis])<1e-14) { if(o[axis]<n.lo[axis]||o[axis]>n.hi[axis]) return false; }
            else { double a=(n.lo[axis]-o[axis])/d[axis],b=(n.hi[axis]-o[axis])/d[axis];
                if(a>b) std::swap(a,b); near=std::max(near,a); far=std::min(far,b); if(far<near) return false; }
        }
        return true;
    }
    bool tri_hit(const Triangle& t,V o,V d,double& distance) const {
        V e1=t.b-t.a,e2=t.c-t.a,p=cross(d,e2); double det=dot(e1,p);
        if(std::abs(det)<1e-12) return false;
        double inv=1.0/det; V s=o-t.a; double u=dot(s,p)*inv;
        if(u<0||u>1) return false;
        V q=cross(s,e1); double v=dot(d,q)*inv; if(v<0||u+v>1) return false;
        double x=dot(e2,q)*inv; if(x<=EPS||x>=distance) return false; distance=x; return true;
    }
    bool visit(int index,V o,V d,Hit& hit,bool any) const {
        const Node& n=nodes[index]; if(!box_hit(n,o,d,hit.t)) return false;
        bool found=false;
        if(n.count) {
            for(int i=n.start;i<n.start+n.count;i++) {
                int idx=order[i]; if(tri_hit(ts[idx],o,d,hit.t)) { hit.tri=idx; found=true; if(any) return true; }
            }
        } else {
            found=visit(n.left,o,d,hit,any); if(found&&any) return true;
            found=visit(n.right,o,d,hit,any)||found;
        }
        return found;
    }
    Hit intersect(V o,V d,bool any=false) const { Hit h; if(!nodes.empty()) visit(0,o,d,h,any); return h; }
};

double radical_inverse(unsigned int bits) {
    double v=0,f=0.5; while(bits) {v+=(bits&1U)*f; bits>>=1U; f*=0.5;} return v;
}
V direction(double u,double v) {
    double yaw=2*PI*(u-0.5),pitch=PI*(0.5-v),cp=std::cos(pitch);
    return {std::sin(yaw)*cp,std::cos(yaw)*cp,std::sin(pitch)};
}
unsigned char encode(double v) {
    v=std::clamp(v,0.0,1.0); double s=v<=0.0031308?12.92*v:1.055*std::pow(v,1.0/2.4)-0.055;
    return static_cast<unsigned char>(std::lround(std::clamp(s,0.0,1.0)*255));
}
void ppm(const std::string& path,const std::vector<unsigned char>& data,int w,int h) {
    std::ofstream out(path,std::ios::binary); if(!out) throw std::runtime_error("Cannot open output: "+path);
    out<<"P6\n"<<w<<" "<<h<<"\n255\n"; out.write(reinterpret_cast<const char*>(data.data()),data.size());
    if(!out) throw std::runtime_error("Failed writing output: "+path);
}
int main(int argc,char** argv) {
    try {
        if(argc!=7) throw std::runtime_error("Usage: renderer scene.txt output-prefix width samples threads shadows");
        int w=std::stoi(argv[3]),h=w/2,samples=std::stoi(argv[4]),threads=std::stoi(argv[5]);
        bool shadows=std::stoi(argv[6])!=0;
        if(w<16||w>8192||w%2||samples<1||samples>64||threads<1||threads>64)
            throw std::runtime_error("Invalid render dimensions/sampling/thread count");
        std::ifstream in(argv[1]); if(!in) throw std::runtime_error("Cannot read scene");
        std::string magic; in>>magic; if(magic!="GGP1") throw std::runtime_error("Unsupported scene format");
        V camera=readv(in),top=readv(in),horizon=readv(in),bottom=readv(in),sun=unit(readv(in));
        double ambient; size_t count; in>>ambient>>count;
        if(count>2000000) throw std::runtime_error("Triangle limit exceeded");
        std::vector<Triangle> input; input.reserve(count);
        for(size_t i=0;i<count;i++) {
            Triangle t; t.a=readv(in);t.b=readv(in);t.c=readv(in);t.rgb=readv(in);in>>t.id;
            t.normal=unit(cross(t.b-t.a,t.c-t.a));t.lo=mn(t.a,mn(t.b,t.c));t.hi=mx(t.a,mx(t.b,t.c));
            t.center=(t.a+t.b+t.c)*(1.0/3.0);input.push_back(t);
        }
        if(!in) throw std::runtime_error("Malformed scene");
        BVH bvh(std::move(input));
        size_t pixels=static_cast<size_t>(w)*h;
        std::vector<unsigned char> rgb(pixels*3),ids(pixels*3);
        std::vector<float> depth(pixels,std::numeric_limits<float>::infinity());
        std::atomic<int> row{0};
        auto shade=[&](V d) {
            Hit hit=bvh.intersect(camera,d);
            if(hit.tri<0) { double t=std::abs(d.z); return horizon*(1-t)+(d.z>=0?top:bottom)*t; }
            const auto& tri=bvh.ts[hit.tri]; V n=tri.normal; if(dot(n,d)>0) n=n*(-1);
            double light=std::max(0.0,dot(n,sun));
            if(shadows&&light>0&&ambient<1) {
                V p=camera+d*hit.t+n*(EPS*10); if(bvh.intersect(p,sun,true).tri>=0) light=0;
            }
            return tri.rgb*(ambient+(1-ambient)*light);
        };
        auto worker=[&]() {
            int y;
            while((y=row.fetch_add(1))<h) for(int x=0;x<w;x++) {
                size_t index=static_cast<size_t>(y)*w+x; V sum;
                for(int s=0;s<samples;s++) {
                    double dx=samples==1?0.5:(s+0.5)/samples;
                    double dy=samples==1?0.5:std::fmod(radical_inverse(static_cast<unsigned int>(s))+0.5/samples,1.0);
                    sum=sum+shade(direction((x+dx)/w,(y+dy)/h));
                }
                sum=sum*(1.0/samples);rgb[index*3]=encode(sum.x);rgb[index*3+1]=encode(sum.y);rgb[index*3+2]=encode(sum.z);
                Hit center=bvh.intersect(camera,direction((x+0.5)/w,(y+0.5)/h));
                if(center.tri>=0) { unsigned int id=static_cast<unsigned int>(bvh.ts[center.tri].id);
                    ids[index*3]=static_cast<unsigned char>(id&255);ids[index*3+1]=static_cast<unsigned char>((id>>8)&255);
                    ids[index*3+2]=static_cast<unsigned char>((id>>16)&255);depth[index]=static_cast<float>(center.t); }
            }
        };
        std::vector<std::thread> pool; for(int i=0;i<threads;i++) pool.emplace_back(worker);
        for(auto& t:pool) t.join();
        std::string prefix=argv[2];ppm(prefix+"-color.ppm",rgb,w,h);ppm(prefix+"-ids.ppm",ids,w,h);
        std::ofstream out(prefix+"-depth.bin",std::ios::binary);
        out.write(reinterpret_cast<const char*>(depth.data()),static_cast<std::streamsize>(depth.size()*sizeof(float)));
        if(!out) throw std::runtime_error("Failed writing depth output");
        return 0;
    } catch(const std::exception& e) { std::cerr<<"renderer: "<<e.what()<<"\n";return 1; }
}
