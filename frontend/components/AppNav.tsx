import Link from "next/link";

interface AppNavProps {
  title?: string;
  trailing?: React.ReactNode;
}

export default function AppNav({ title, trailing }: AppNavProps) {
  return (
    <header className="app-nav">
      <div className="app-nav__inner">
        <div className="app-nav__left">
          <Link href="/" className="app-nav__brand">
            Deep Research
          </Link>
          {title && (
            <>
              <span className="app-nav__divider" aria-hidden="true" />
              <span className="app-nav__title">{title}</span>
            </>
          )}
        </div>
        {trailing && (
          <div className="app-nav__right">
            {trailing}
          </div>
        )}
      </div>
    </header>
  );
}
