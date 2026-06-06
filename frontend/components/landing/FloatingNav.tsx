import MagneticButton from "./MagneticButton";

const LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Agents", href: "#agents" },
  { label: "Stack", href: "#stack" },
];

export default function FloatingNav() {
  return (
    <nav className="landing-nav" aria-label="Page navigation">
      <div className="landing-nav__pill">
        <span className="landing-nav__brand">Deep Research</span>

        <div className="landing-nav__links">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="landing-nav__link" data-cursor-hover>
              {link.label}
            </a>
          ))}
        </div>

        <MagneticButton href="/app" className="landing-nav__cta">
          Launch App
        </MagneticButton>
      </div>
    </nav>
  );
}
