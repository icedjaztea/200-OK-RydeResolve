'use client';
import {useState} from 'react';
import Link from 'next/link';

export default function Landing(){
  const [showLab,setShowLab]=useState(false);
  return <main className="landing">
    <header className="landing-hero">
      <div className="landing-brand">
        <div className="landing-logo">R</div>
        <div><h1>RydeResolve</h1><p>Policy-grounded dispute resolution demo</p></div>
      </div>
      <div className="demo-banner">SYNTHETIC DEMO · NO REAL PAYMENTS</div>
    </header>

    <section className="landing-intro">
      <h2>Resolve trip disputes through structured policy and evidence</h2>
      <p className="landing-subtitle">A synthetic demonstration of a multi-agent dispute resolution workflow. Six independent AI agents analyze each case, a deterministic policy engine validates outcomes, and a human reviewer makes the final call. This is a demo — no real payments, accounts, or notifications are involved.</p>
    </section>

    <div className="role-grid">
      <Link href="/rider" className="role-card rider-accent">
        <div className="role-icon">R</div>
        <h3>Rider Portal</h3>
        <p>File a dispute, respond to clarification requests, and check your case status</p>
        <span className="role-cta">Enter as Rider →</span>
      </Link>
      <Link href="/driver" className="role-card driver-accent">
        <div className="role-icon">D</div>
        <h3>Driver Portal</h3>
        <p>View cases involving you, respond to requests, and check outcomes</p>
        <span className="role-cta">Enter as Driver →</span>
      </Link>
      <Link href="/reviewer" className="role-card reviewer-accent">
        <div className="role-icon">Rv</div>
        <h3>Reviewer Workbench</h3>
        <p>Full investigation workbench with evidence, advocates, and decision tools</p>
        <span className="role-cta">Enter as Reviewer →</span>
      </Link>
    </div>

    <div className="lab-link-section">
      <button className="lab-toggle" onClick={()=>setShowLab(!showLab)}>{showLab?'Hide':'Show'} full dashboard</button>
      {showLab&&<div className="lab-link-card">
        <p className="muted">The full dashboard shows complete case details including all roles, agents, and events in one view. This is a reviewer-equivalent view for technical inspection.</p>
        <Link href="/lab" className="lab-enter">Full dashboard →</Link>
      </div>}
    </div>

    <footer className="landing-footer">
      RydeResolve is a synthetic demo environment. No real Ryde account, payment, or notification integrations exist. <br/>All data is synthetic. Do not enter real personal information.
    </footer>
  </main>;
}
