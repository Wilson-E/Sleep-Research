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

function SnapshotStat({ label, value }) {
  return (
    <div className="home-snapshot-stat">
      <div className="home-snapshot-label">{label}</div>
      <div className="home-snapshot-value">{value}</div>
    </div>
  )
}

export default function HomePage() {
  return (
    <div className="home-page">
      <nav className="home-top-nav">
        <div className="home-nav-inner">
          <div className="home-brand">Vitality Core</div>
          <div className="home-nav-links">
            <Link to="/science">Science</Link>
            <a href="#circadian">Circadian</a>
            <a href="#nutrition">Nutrition</a>
            <a href="#recovery">Recovery</a>
          </div>
          <Link className="home-nav-cta" to="/simulator">Try Simulator</Link>
        </div>
      </nav>

      <main>
        <section className="home-hero" id="science">
          <div className="home-hero-content">
            <span className="home-pill">The Clinical Sanctuary</span>
            <h1>
              Your Biological Baseline, <span>Reimagined.</span>
            </h1>
            <p>
              Optimize your sleep, nutrition, and circadian rhythm with data-driven simulation. Experience an
              interface that breathes with your biological data.
            </p>
            <div className="home-hero-actions">
              <Link className="home-btn home-btn-primary" to="/simulator">Try Free Simulator</Link>
              <Link className="home-btn home-btn-secondary" to="/science">Learn the Science</Link>
            </div>
          </div>
          <div className="home-hero-visual" aria-hidden="true">
            <div className="orb one" />
            <div className="orb two" />
            <div className="orb three" />
          </div>
        </section>

        <section className="home-features" id="circadian">
          <div className="home-container home-feature-grid">
            <FeatureCard
              icon="wb_sunny"
              title="Circadian Precision"
              description="Align your light exposure and activity windows with your natural chronotype for peak alertness."
              tone="secondary"
            />
            <FeatureCard
              icon="restaurant"
              title="Metabolic Timing"
              description="Optimize nutrient absorption by timing consumption with your body's peak metabolic rate."
              tone="primary"
            />
            <FeatureCard
              icon="favorite"
              title="Neural Recovery"
              description="Advanced HRV and sleep-stage tracking to ensure deep parasympathetic restoration every night."
              tone="tertiary"
            />
          </div>
        </section>

        <section className="home-snapshot" id="snapshot">
          <div className="home-container home-snapshot-grid">
            <div>
              <span className="home-pill home-pill-green">Optimized State</span>
              <h2>Clinical Authority in Every Data Point.</h2>
              <p>
                Our proprietary Sleep Score Simulator does not just track data, it models potential outcomes.
                Adjust your evening routine in real-time to see how it shifts your biological baseline.
              </p>
              <ul className="home-check-list">
                <li>
                  <span className="material-symbols-outlined">check_circle</span>
                  <div>
                    <h4>Predictive Modeling</h4>
                    <p>See your sleep score before you even close your eyes.</p>
                  </div>
                </li>
                <li>
                  <span className="material-symbols-outlined">check_circle</span>
                  <div>
                    <h4>Bio-Feedback Loops</h4>
                    <p>Real-time adjustments based on HRV and ambient light levels.</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="home-snapshot-card-wrap">
              <div className="home-snapshot-card">
                <div className="home-snapshot-head">
                  <h4>Sleep Score Simulator</h4>
                  <span>Live Data</span>
                </div>

                <div className="home-score-ring">
                  <div className="home-score-inner">
                    <div className="home-score-value">84</div>
                    <div className="home-score-state">Optimized</div>
                  </div>
                </div>

                <div className="home-snapshot-stats">
                  <SnapshotStat label="Deep Sleep" value="2h 14m" />
                  <SnapshotStat label="Latency" value="12m" />
                </div>
              </div>
              <div className="home-snapshot-glow" />
            </div>
          </div>
        </section>

        <section className="home-metrics" id="nutrition">
          <div className="home-container home-metric-grid">
            <div>
              <strong>12k+</strong>
              <span>Bio-optimized</span>
            </div>
            <div>
              <strong>45+</strong>
              <span>Studies integrated</span>
            </div>
            <div>
              <strong>8.5h</strong>
              <span>Avg sleep goal</span>
            </div>
          </div>
        </section>

        <section className="home-cta" id="recovery">
          <div className="home-container home-cta-inner">
            <div className="home-brand-mini">Vitality Core</div>
            <h2>
              Start Your Journey to
              <br />
              Human Excellence.
            </h2>
            <Link className="home-btn home-btn-primary home-btn-big" to="/simulator">
              Begin Optimization
            </Link>
          </div>
        </section>
      </main>

      <footer className="home-footer">
        <div className="home-container home-footer-grid">
          <div>
            <div className="home-footer-title">Vitality Core</div>
            <p>
              The leading platform for human bio-optimization through precision data simulation.
            </p>
          </div>
          <div>
            <h4>Product</h4>
            <a href="#science">Science</a>
            <a href="#snapshot">Methodology</a>
            <a href="#nutrition">Research</a>
          </div>
          <div>
            <h4>Company</h4>
            <a href="#">About Us</a>
            <a href="#">Careers</a>
            <a href="#">Press Kit</a>
          </div>
          <div>
            <h4>Legal</h4>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Compliance</a>
          </div>
        </div>

        <div className="home-container home-footer-bottom">
          <p>© 2026 Vitality Core. Engineered for Human Excellence.</p>
          <div>
            <span className="material-symbols-outlined">share</span>
            <span className="material-symbols-outlined">language</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
