'use client';
import {useState} from 'react';
import Link from 'next/link';

const ROLES=[
  {id:'rider',label:'Rider',href:'/rider',icon:'R',tagline:'File a dispute, track your case, answer clarifications, and see outcomes in plain language.',
   accent:'rider-accent'},
  {id:'driver',label:'Driver',href:'/driver',icon:'D',tagline:'View case history, respond to requests, and check outcomes.',
   accent:'driver-accent'},
  {id:'reviewer',label:'Reviewer',href:'/reviewer',icon:'Rv',tagline:'Operational queue, advocate perspectives, policy gates, escalation, decision packet.',
   accent:'reviewer-accent'},
];

export default function LandingPage(){
  const [showLab,setShowLab]=useState(false);

  return <main className="landing">
    <header className="landing-hero">
      <div className="landing-brand">
        <div className="landing-logo">R</div>
        <div>
          <h1>RydeResolve</h1>
          <p>Policy-grounded dispute resolution · Tencent Cloud AI Agent Hackathon</p>
        </div>
      </div>
      <div className="demo-banner">HACKATHON DEMO · SYNTHETIC DATA · NO REAL PAYMENTS</div>
    </header>

    <section className="landing-intro">
      <h2>Choose your role to continue</h2>
      <p className="landing-subtitle">
        Each portal uses role-specific demo passcodes from the backend. The backend independently
        authorizes every request — UI separation is not production user isolation. All data is
        synthetic. The demo API is not user-isolated; role filtering does not ensure real privacy.
      </p>
    </section>

    <div className="role-grid">
      {ROLES.map(r=>(
        <Link key={r.id} href={r.href} className={`role-card ${r.accent}`}>
          <div className="role-icon">{r.icon}</div>
          <h3>{r.label}</h3>
          <p>{r.tagline}</p>
          <span className="role-cta">Enter portal →</span>
        </Link>
      ))}
    </div>

    <section className="lab-link-section">
      <button className="lab-toggle" onClick={()=>setShowLab(!showLab)}>
        {showLab?'Hide':'Show'} full dashboard
      </button>
      {showLab&&(
        <div className="lab-link-card">
          <p className="muted">The complete lab dashboard with all features — case queue, processing,
          advocate outputs, reviewer packet, learning loop, evaluation report, and event traces.</p>
          <Link href="/lab" className="lab-enter">Open /lab dashboard →</Link>
        </div>
      )}
    </section>

    <footer className="landing-footer">
      RydeResolve is a synthetic hackathon prototype. No Ryde APIs, customer data, payments,
      or account actions are connected. All data is synthetic.
    </footer>
  </main>;
}
