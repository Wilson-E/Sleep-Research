import { Link } from 'react-router-dom'
import './HomePage.css'

function FeatureCard({ icon, title, description, tone }) {
  return (
    <article className="home-feature-card">
      <div className={`home-feature-icon ${tone}`}>
        <span className="material-symbols-outlined">{icon}</span>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  )
}

export default function HomePage() {
  return (
    <div className="home-page">
      <nav className="home-top-nav">
        <div className="home-nav-inner">
          <div className="home-brand">Vitality Core</div>
          <div className="home-nav-links">
            <Link to="/simulator">Simulator</Link>
            <Link to="/history">History</Link>
            <Link to="/science">Science</Link>
          </div>
          <Link className="home-nav-cta" to="/simulator">Try Simulator</Link>
        </div>
      </nav>

      <main>
        <section className="home-hero">
          <div className="home-hero-content">
            <span className="home-pill">Penn State DS340W, Group 39</span>
            <h1>
              A Pathway-Based Sleep Quality <span>Simulator.</span>
            </h1>
            <p>
              Vitality Core predicts a 0 to 100 nightly sleep score from everyday lifestyle inputs
              (caffeine, alcohol, meal timing, evening light, and evening diet). Each pathway uses
              published regression coefficients; every point gained or lost traces back to a specific
              study. Personalization is Bayesian and learns from a few logged nights.
            </p>
            <div className="home-hero-actions">
              <Link className="home-btn home-btn-primary" to="/simulator">Try the Simulator</Link>
              <Link className="home-btn home-btn-secondary" to="/science">Read the Science</Link>
              <Link className="home-btn home-btn-secondary" to="/history">Log a Night</Link>
            </div>
          </div>
          <div className="home-hero-visual" aria-hidden="true">
            <div className="orb one" />
            <div className="orb two" />
            <div className="orb three" />
          </div>
        </section>

        <section className="home-features">
          <div className="home-container home-feature-grid">
            <FeatureCard
              icon="wb_sunny"
              title="Circadian Inputs"
              description="Light exposure and meal timing pathways based on Didikoglu et al. (2023) and Kim et al. (2024). See the Science page for the full coefficient sources."
              tone="secondary"
            />
            <FeatureCard
              icon="restaurant"
              title="Metabolic Timing"
              description="Chrononutrition effects translated into per-hour odds ratios, with a cross-pathway mediator from Soares et al. (2025) for evening diet composition."
              tone="primary"
            />
            <FeatureCard
              icon="favorite"
              title="Bayesian Personalization"
              description="Each coefficient starts at its literature value and updates toward a user's own sensitivity profile after five to ten logged nights via Normal-Normal conjugate updating."
              tone="tertiary"
            />
          </div>
        </section>

        <section className="home-cta">
          <div className="home-container home-cta-inner">
            <div className="home-brand-mini">Vitality Core</div>
            <h2>
              Try a prediction,
              <br />
              or log a night and personalize it.
            </h2>
            <div className="home-hero-actions">
              <Link className="home-btn home-btn-primary home-btn-big" to="/simulator">
                Open Simulator
              </Link>
              <Link className="home-btn home-btn-secondary home-btn-big" to="/history">
                Log a Night
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="home-footer">
        <div className="home-container home-footer-grid">
          <div>
            <div className="home-footer-title">Vitality Core</div>
            <p>
              Research prototype developed for DS340W at Penn State University. Pathway coefficients
              are sourced from peer-reviewed studies; see the Science page for the full list.
            </p>
          </div>
          <div>
            <h4>Pages</h4>
            <Link to="/simulator">Simulator</Link>
            <Link to="/history">History</Link>
            <Link to="/science">Science</Link>
          </div>
          <div>
            <h4>Source</h4>
            <a href="https://github.com/Wilson-E/Sleep-Research" target="_blank" rel="noreferrer">
              GitHub repository
            </a>
          </div>
        </div>

        <div className="home-container home-footer-bottom">
          <p>Penn State DS340W, Group 39. Research prototype; see the paper for details.</p>
        </div>
      </footer>
    </div>
  )
}
