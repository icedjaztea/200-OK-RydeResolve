import React from 'react';
import {Img,staticFile,useCurrentFrame,interpolate,Easing} from 'remotion';
const P='#e8336a';
export const SPLIT_IDS=['intake','evidence','agents','refund','other','driver','outcome'];
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const ImagePanel:React.FC<{src:string;width:number,from?:number,to?:number,duration:number}>=({src,width,from=0,to=from,duration})=>{const f=useCurrentFrame();const y=interpolate(f,[40,Math.max(41,duration-80)],[from,to],{...clamp,easing:Easing.bezier(.33,0,.15,1)});return <Img src={staticFile('textures/'+src+'.png')} style={{width,position:'absolute',top:-y,left:'50%',transform:'translateX(-50%)'}}/>};
export const SplitView:React.FC<{shot:any}>=({shot})=>{const f=useCurrentFrame();let left='rider-trip-phone',right='split-fare-evidence',role='RIDER',ly=155,ly2=320,ry=0,ry2=140;let note='Trip context and the evidence used to assess it';let lw=620;
 if(shot.id==='evidence'){ly=175;ly2=175;ry=0;ry2=0;}
 if(shot.id==='intake'||shot.id==='other'){left='rider-report-phone';right=shot.id==='other'&&f>=230?'split-other-reclassified':'split-other-review';ly=75;ly2=330;ry=0;ry2=shot.id==='other'&&f>=230?330:200;note=shot.id==='intake'?'Rider submission → reviewer classification':'Original report → classification and audit trail';}
 if(shot.id==='agents'){const driver=f>=Math.floor(shot.duration/2);left=driver?'driver-trip':'rider-trip-phone';role=driver?'DRIVER':'RIDER';right='split-fare-agents';ly=driver?0:175;ly2=ly;ry=driver?190:0;ry2=ry;note='Both parties’ trip context → separate advocate findings';}
 if(shot.id==='refund'||shot.id==='outcome'){left='rider-outcome-phone';right='split-fare-overview';ly=shot.id==='refund'?410:880;ly2=shot.id==='refund'?700:1140;ry=shot.id==='refund'?0:250;ry2=shot.id==='refund'?150:325;note='Same case: DISP-003 · SGD 4.50 simulated refund';}
 if(shot.id==='driver'){left='driver-requested-card';right='request-more-info';role='DRIVER';ly=0;ly2=0;ry=0;ry2=0;note='Reviewer question → driver action needed · replies remain unverified';lw=620;}
 if(shot.id==='outcome'){left='split-rider-progress';lw=530;ly=0;ly2=0;}
 // Driver trip is a retained 1920px-wide browser screenshot, focused on its real trip card.
 const driverTrip=shot.id==='agents'&&role==='DRIVER';
 return <>
 <div style={{position:'absolute',left:95,top:274,width:650,fontSize:32,fontWeight:800,color:P,letterSpacing:1}}>{role} VIEW</div>
 <div style={{position:'absolute',left:790,top:274,width:1035,fontSize:32,fontWeight:800,color:P,letterSpacing:1}}>REVIEWER VIEW</div>
 <div style={{position:'absolute',left:95,top:324,width:650,height:548,overflow:'hidden',borderRadius:18,border:'1px solid #d8ccd2',background:'#fff'}}>
 {shot.id==='refund'?<><Img src={staticFile('textures/split-rider-decision.png')} style={{width:620,position:'absolute',left:15,top:15}}/><Img src={staticFile('textures/split-rider-refund.png')} style={{width:620,position:'absolute',left:15,top:300}}/><div style={{position:'absolute',left:30,top:440,fontSize:30,color:P,fontWeight:700}}>Simulated refund · No funds moved</div></>:driverTrip?<Img src={staticFile('textures/driver-trip.png')} style={{position:'absolute',width:2484,left:-917,top:-185}}/>:<ImagePanel src={left} width={lw} from={ly} to={ly2} duration={shot.duration}/>}
 </div>
 <div style={{position:'absolute',left:790,top:324,width:1035,height:548,overflow:'hidden',borderRadius:18,border:'1px solid #d8ccd2',background:'#fff'}}><ImagePanel src={right} width={1035} from={ry} to={ry2} duration={shot.duration}/>{shot.id==='driver'&&<div style={{position:'absolute',left:30,right:30,top:350,fontSize:32,color:'#534659',lineHeight:1.5}}>Request a timestamped message or call reference.<br/><strong style={{color:P}}>User replies require supporting evidence.</strong></div>}</div>
 <div style={{position:'absolute',left:95,top:892,right:95,fontSize:30,fontWeight:650,color:'#534659'}}>{note}<span style={{float:'right',fontSize:24,fontWeight:500}}>Recorded stages · synthetic data</span></div>
 </>;
};
