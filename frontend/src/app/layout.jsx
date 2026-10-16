import './globals.css';
export const metadata = {
  title:'RydeResolve — Dispute Resolution Demo',
  description:'Policy-grounded synthetic dispute resolution workflow demo',
};
export default function RootLayout({children}){
  return <html lang="en">
    <body>
      {children}
      <div className="demo-badge">SYNTHETIC DEMO · NO REAL PAYMENTS</div>
    </body>
  </html>;
}
