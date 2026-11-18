import { useLanguage, locale } from '../lib/i18n';
import '../styles/dashboard-donut.css';

export function DashboardDonut({ open, done, cancelled = 0 }: { open: number; done: number; cancelled?: number }) {
  const en = useLanguage() === 'en';
  const total = open + done + cancelled;
  const segments = [
    { label: en ? 'Cancelled' : 'ยกเลิกแล้ว', count: cancelled, color: '#8b98a5' },
    { label: en ? 'In progress' : 'กำลังดำเนินการ', count: open, color: '#d99016' },
    { label: en ? 'Completed' : 'ปิดงานแล้ว', count: done, color: '#0080c6' },
  ];
  let offset = 0;
  return <div className="panel dashboard-donut">
    <div className="dashboard-donut-heading"><span>TRIP OVERVIEW</span><h2>{en ? 'Trip status distribution' : 'สัดส่วนสถานะเที่ยวรถ'}</h2><p>{en ? 'All trips in the system' : 'ภาพรวมเที่ยวรถทั้งหมดในระบบ'}</p></div>
    <div className="dashboard-donut-ring" role="img" aria-label={segments.map(s => `${s.label} ${s.count}`).join(', ')}>
      <svg viewBox="0 0 220 220" aria-hidden="true">
        <circle cx="110" cy="110" r="78" fill="none" stroke="#e5edf4" strokeWidth="24"/>
        {segments.map(segment => {
          const length = total ? segment.count / total * 100 : 0;
          const start = offset; offset += length;
          return segment.count > 0 && <circle key={segment.label} cx="110" cy="110" r="78" fill="none" stroke={segment.color} strokeWidth="24" pathLength="100" strokeDasharray={`${Math.max(0,length-(length===100 ? 0 : Math.min(1,length/4)))} 100`} strokeDashoffset={-start} transform="rotate(-90 110 110)"/>;
        })}
      </svg>
      <div className="dashboard-donut-center"><small>{en ? 'Total trips' : 'เที่ยวรถทั้งหมด'}</small><strong>{total.toLocaleString(locale())}</strong><span>{en ? 'trips' : 'เที่ยว'}</span></div>
    </div>
    <div className="dashboard-donut-legend">{segments.map(segment => <div key={segment.label}><i style={{background:segment.color}}/><span>{segment.label}</span><strong>{segment.count.toLocaleString(locale())}</strong><small>{total ? Math.round(segment.count/total*100) : 0}%</small></div>)}
      {!total && <p>{en ? 'No trips yet' : 'ยังไม่มีเที่ยวรถในระบบ'}</p>}
    </div>
  </div>;
}
