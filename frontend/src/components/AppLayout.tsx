import type { CSSProperties } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { pantallas } from '../routes'
import styles from './AppLayout.module.css'

export default function AppLayout() {
  const { pathname } = useLocation()
  const actual = pantallas.find((p) => p.path === pathname)

  const estiloFranja: CSSProperties | undefined = actual?.area
    ? { background: `var(--${actual.area})` }
    : undefined

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <span className={styles.logo}>Ciclo</span>
        <nav className={styles.nav}>
          {pantallas.map((p) => (
            <NavLink
              key={p.path}
              to={p.path}
              end
              className={({ isActive }) =>
                isActive ? `${styles.link} ${styles.activo}` : styles.link
              }
            >
              {p.label}
            </NavLink>
          ))}
        </nav>
        <div className={styles.derecha}>
          <span>Guardia de 7 a 19 h</span>
          <span className={styles.operador}>Operador</span>
        </div>
      </header>

      {actual?.area && (
        <div className={styles.franja} style={estiloFranja}>
          {actual.franja}
        </div>
      )}

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
