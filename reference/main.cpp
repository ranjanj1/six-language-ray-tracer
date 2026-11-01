#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
struct V { double x,y,z; };
V operator+(V a,V b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
V operator-(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
V operator-(V a){return {-a.x,-a.y,-a.z};}
V operator*(V a,double t){return {a.x*t,a.y*t,a.z*t};}
V operator*(V a,V b){return {a.x*b.x,a.y*b.y,a.z*b.z};}
V operator/(V a,double t){return a*(1/t);}
double dot(V a,V b){return (a.x*b.x+a.y*b.y)+a.z*b.z;}
V unit(V a){return a/std::sqrt(dot(a,a));}
uint32_t state=42;
double random01(){state^=state<<13;state^=state>>17;state^=state<<5;return double(state)/4294967296.0;}
V random_unit(){for(;;){double x=2*random01()-1;double y=2*random01()-1;double z=2*random01()-1;V v{x,y,z};double q=dot(v,v);if(q<=1&&q>1e-160)return v*(1/std::sqrt(q));}}
struct Sphere{V center;double radius;int material;V albedo;double fuzz;};
const Sphere scene[]={{{0,-100.5,-1},100,0,{.8,.8,0},0},{{0,0,-1.2},.5,0,{.1,.2,.5},0},{{-1,0,-1},.5,2,{1,1,1},0},{{1,0,-1},.5,1,{.8,.6,.2},.3}};
V reflect(V u,V n){return u-n*(2*dot(u,n));}
V trace(V origin,V direction,int depth){
 if(depth<=0)return {0,0,0};
 double closest=std::numeric_limits<double>::infinity(); const Sphere* hit=nullptr;
 for(const auto& s:scene){V oc=s.center-origin;double a=dot(direction,direction),h=dot(direction,oc),c=dot(oc,oc)-s.radius*s.radius,disc=h*h-a*c;if(disc<0)continue;double root=(h-std::sqrt(disc))/a;if(!(root>.001&&root<closest)){root=(h+std::sqrt(disc))/a;if(!(root>.001&&root<closest))continue;}closest=root;hit=&s;}
 if(!hit){V u=unit(direction);double a=.5*(u.y+1);return V{1,1,1}*(1-a)+V{.5,.7,1}*a;}
 V p=origin+direction*closest,outward=(p-hit->center)/hit->radius;bool front=dot(direction,outward)<0;V n=front?outward:-outward,scattered;
 if(hit->material==0){scattered=n+random_unit();if(std::abs(scattered.x)<1e-8&&std::abs(scattered.y)<1e-8&&std::abs(scattered.z)<1e-8)scattered=n;}
 else if(hit->material==1){V u=unit(direction);V r=reflect(u,n);V jitter=random_unit();scattered=r+jitter*hit->fuzz;if(dot(scattered,n)<=0)return {0,0,0};}
 else{double eta=front?1/1.5:1.5;V u=unit(direction);double cosine=std::min(dot(-u,n),1.0),sine=std::sqrt(1-cosine*cosine);bool bounce=eta*sine>1;
 if(!bounce){double r0=(1-eta)/(1+eta);r0=r0*r0;double x=1-cosine,x2=x*x,x5=(x2*x2)*x,R=r0+(1-r0)*x5;double draw=random01();bounce=R>draw;}
 if(bounce)scattered=reflect(u,n);else{V perp=(u+n*cosine)*eta;V parallel=n*(-std::sqrt(std::abs(1-dot(perp,perp))));scattered=perp+parallel;}}
 return hit->albedo*trace(p,scattered,depth-1);
}
int encode(double s){double g=std::sqrt(std::max(0.0,s/200));return int(256*std::min(.999,std::max(0.0,g)));}
int main(){std::ofstream out("out.ppm");if(!out)return 1;out<<"P3\n400 225\n255\n";V vu{2*(400.0/225),0,0},vv{0,-2,0},du=vu/400,dv=vv/225,upper=(V{0,0,-1}-vu*.5)-vv*.5,p00=upper+(du+dv)*.5;
 for(int j=0;j<225;++j)for(int i=0;i<400;++i){V center=(p00+du*i)+dv*j,sum{0,0,0};for(int s=0;s<200;++s){double ox=random01()-.5;double oy=random01()-.5;V point=(center+du*ox)+dv*oy;sum=sum+trace({0,0,0},point,10);}out<<encode(sum.x)<<' '<<encode(sum.y)<<' '<<encode(sum.z)<<'\n';}out.close();return out?0:1;}
