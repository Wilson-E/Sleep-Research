import { Link } from 'react-router-dom'
import './SciencePage.css'

function ScienceSection({ icon, title, children }) {
  return (
    <section className="science-section">
      <div className="science-section-header">
        <span className="material-symbols-outlined">{icon}</span>
        <h2>{title}</h2>
      </div>
      <div className="science-section-content">{children}</div>
    </section>
  )
}

function StudyCallout({ author, finding }) {
  return (
    <div className="study-callout">
      <span className="callout-icon material-symbols-outlined">auto_awesome</span>
      <div>
        <strong>{author}:</strong> {finding}
      </div>
    </div>
  )
}

export default function SciencePage() {
  return (
    <div className="science-page">
      <header className="science-header">
        <div className="science-header-content">
          <div className="science-header-top-action">
            <Link to="/" className="science-back-link">
              <span className="material-symbols-outlined">arrow_back</span>
              Back to Dashboard
            </Link>
          </div>
          <h1>The Science Behind Sleep Optimization</h1>
          <p>
            Understand how biological factors influence sleep quality and duration. This guide is based on
            peer-reviewed research from major sleep and chronobiology studies.
          </p>
        </div>
      </header>

      <main className="science-main">
        <ScienceSection icon="local_cafe" title="Caffeine & Sleep Quantity">
          <div className="science-text">
            <p>
              Caffeine is a central nervous system stimulant that blocks adenosine receptors in the brain.
              Adenosine naturally accumulates during waking hours and signals to your brain that it's time to
              sleep. By blocking adenosine, caffeine prevents this sleep signal and keeps you alert.
            </p>
            <StudyCallout
              author="Song & Walker (2023)"
              finding="Every cup of caffeinated beverage consumed predicted a 10.4-minute reduction in sleep duration. For someone consuming 1.14 cups per day, this translates to losing over an hour of sleep per week."
            />
            <p>
              <strong>Mechanism:</strong> Caffeine's effects peak 30-60 minutes after consumption and can last
              5-6 hours or longer. Even consuming caffeine in the afternoon (e.g., 4:00 PM) can significantly
              impact nighttime sleep.
            </p>
            <p>
              <strong>Important note:</strong> While caffeine reduces sleep amount, many people don't perceive
              their sleep quality as worse. This means the negative effects of caffeine often go unnoticed,
              leading to continued consumption despite sleep debt accumulation.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="local_drink" title="Alcohol & Sleep Quality">
          <div className="science-text">
            <p>
              Alcohol initially acts as a sedative, making it easier to fall asleep. However, it significantly
              disrupts sleep quality through multiple physiological mechanisms.
            </p>
            <StudyCallout
              author="Song & Walker (2023)"
              finding="Each glass of alcohol consumed predicted a 3-point decline in subjective sleep quality on a 100-point scale the next day. This effect was statistically significant and consistent across nights."
            />
            <p>
              <strong>Three main mechanisms disrupt sleep:</strong>
            </p>
            <ul className="science-list">
              <li>
                <strong>Sleep Architecture Disruption:</strong> Alcohol induces slow-wave sleep (the deepest sleep
                stage) earlier in the night. When alcohol is metabolized, this stage becomes suppressed, leading
                to fragmented, lighter sleep in the second half of the night.
              </li>
              <li>
                <strong>REM Sleep Suppression:</strong> Alcohol suppresses REM (rapid eye movement) sleep, which
                plays crucial roles in memory consolidation and emotional regulation. When blood alcohol drops,
                the brain rebounds with increased REM intensity, causing more nighttime awakenings.
              </li>
              <li>
                <strong>Sympathetic Nervous System Activation:</strong> Alcohol increases heart rate variability,
                blood pressure, and sympathetic activity during sleep—all markers of a stressed nervous system
                rather than restorative sleep.
              </li>
            </ul>
            <p>
              Unlike caffeine, alcohol typically does NOT reduce total sleep duration but severely degrades sleep
              quality and promotes fragmentation.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="schedule" title="Meal Timing & Chrononutrition">
          <div className="science-text">
            <p>
              When you eat is nearly as important as what you eat. Your digestive system, hormone production,
              and circadian rhythm are tightly synchronized with meal timing.
            </p>
            <StudyCallout
              author="Kim et al. (2024)"
              finding="Each additional hour between wake time and first eating was associated with a 19% increase in the odds of poor sleep timing and a 21% increase in poor sleep duration."
            />
            <StudyCallout
              author="Kim et al. (2024)"
              finding="Each additional hour between last eating and bedtime was associated with 9% higher odds of poor sleep duration."
            />
            <p>
              <strong>Key findings on meal timing:</strong>
            </p>
            <ul className="science-list">
              <li>
                <strong>Breakfast Timing:</strong> Eating soon after waking helps sync your circadian rhythm to
                the day-night cycle. Delayed breakfast is associated with worse sleep timing and duration.
              </li>
              <li>
                <strong>Dinner Timing:</strong> Eating too close to bedtime (within 1-3 hours) can disrupt sleep
                due to active digestion and stomach acid production while lying down.
              </li>
              <li>
                <strong>Eating Window:</strong> A longer eating window (more distributed meals) is associated with
                better sleep. Very restricted eating windows (eating all calories in a short timeframe) correlate
                with shorter sleep duration.
              </li>
            </ul>
            <p>
              The optimal pattern appears to be eating within 1-2 hours of waking, finishing dinner 3+ hours
              before bed, and spreading meals across a 10-12 hour window.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="wb_sunny" title="Light Exposure & Circadian Rhythm">
          <div className="science-text">
            <p>
              Light is the most powerful regulator of your circadian rhythm—your internal 24-hour biological
              clock. The timing and intensity of light exposure directly controls melatonin production and sleep
              timing.
            </p>
            <p>
              <strong>Morning Light (250+ lux recommended):</strong> Bright morning light exposure signals to your
              brain that it's daytime. This advances your circadian rhythm, promoting earlier sleep onset at
              night and better sleep quality overall. This effect is strongest within 1-3 hours of waking.
            </p>
            <p>
              <strong>Evening Light (minimize before bed):</strong> Blue light from screens and bright overhead
              lights suppress melatonin production, the hormone that signals your brain it's time to sleep. Dim
              warm light in the 1-2 hours before bed supports melatonin production.
            </p>
            <p>
              <strong>Light During Sleep:</strong> Any light exposure during sleep—from phone screens or hallway
              lights—disrupts sleep architecture and impairs melatonin restoration. Even brief light exposure can
              wake you unconsciously.
            </p>
            <p>
              The simulator tracks light in lux (a measure of light intensity). Aim for 250+ lux in morning
              sunlight and keep evening light below 30 lux for optimal sleep.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="monitor_heart" title="Heart Rate Variability (HRV) & Recovery">
          <div className="science-text">
            <p>
              Heart Rate Variability (HRV) is the variation in time between heartbeats. It's a marker of
              parasympathetic nervous system activity—your "rest and digest" system. Higher HRV indicates better
              recovery and autonomic balance.
            </p>
            <p>
              <strong>RMSSD (Root Mean Square of Successive Differences):</strong> This is the most validated HRV
              metric for recovery assessment. It measures the variability between consecutive heartbeats in
              milliseconds.
            </p>
            <p>
              <strong>What higher HRV means for sleep:</strong>
            </p>
            <ul className="science-list">
              <li>Better parasympathetic tone (relaxation response)</li>
              <li>Improved recovery from training or stress</li>
              <li>More stable circadian rhythm</li>
              <li>Better sleep quality and resilience</li>
              <li>Lower inflammation and cardiovascular stress</li>
            </ul>
            <p>
              Factors that improve HRV: consistent sleep schedule, stress management, regular exercise,
              minimizing alcohol, and adequate hydration.
            </p>
            <p>
              A baseline RMSSD of 50+ ms is considered good; 30-50 ms is moderate; below 30 ms may indicate poor
              recovery or excessive stress.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="favorite" title="Resting Heart Rate & Sleep">
          <div className="science-text">
            <p>
              Resting heart rate (RHR)—your heart rate when completely at rest—is an indicator of cardiovascular
              efficiency and autonomic balance. Lower resting heart rates are associated with better fitness,
              recovery, and sleep quality.
            </p>
            <p>
              <strong>RHR and sleep connection:</strong> Chronic sleep deprivation elevates resting heart rate by
              increasing sympathetic nervous system activity. Conversely, improved sleep quality and quantity lead
              to lower resting heart rates.
            </p>
            <p>
              <strong>Typical ranges:</strong>
            </p>
            <ul className="science-list">
              <li>Athletic adults: 40-60 bpm</li>
              <li>Healthy adults: 60-80 bpm</li>
              <li>Poor fitness or recovery: 80+ bpm</li>
            </ul>
            <p>
              As you improve sleep habits, you should observe a gradual decrease in resting heart rate as a sign
              of better recovery and cardiovascular adaptation.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="insights" title="Caffeine-Alcohol Interaction">
          <div className="science-text">
            <p>
              An interesting discovery: when caffeine and alcohol are consumed on the same day, they partially
              offset each other's effects on sleep quantity (though not quality).
            </p>
            <StudyCallout
              author="Song & Walker (2023)"
              finding="When evening alcohol was consumed following daytime caffeine intake, the normally detrimental impact of caffeine on sleep amount was partially prevented, leading to slightly more sleep. However, this doesn't mean using alcohol to counteract caffeine is beneficial."
            />
            <p>
              <strong>Why this happens:</strong> Caffeine and alcohol have opposite effects on the nervous system.
              Caffeine is a stimulant; alcohol is a depressant. When both are present, they can mask each other's
              effects on perceived sleep.
            </p>
            <p>
              <strong>The real problem:</strong> While sleep quantity may be slightly better, hidden sleep quality
              problems persist. Users may unconsciously self-medicate—using alcohol at night to counteract daytime
              caffeine, and vice versa—without realizing they're trading one sleep problem for another.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="science" title="Sleep Health Dimensions">
          <div className="science-text">
            <p>
              Modern sleep science recognizes that sleep isn't just about quantity (duration). The American Heart
              Association identifies multiple dimensions of sleep health:
            </p>
            <ul className="science-list">
              <li>
                <strong>Duration:</strong> 7-9 hours per night for adults (less than 7 or more than 9 hours is
                associated with worse health outcomes)
              </li>
              <li>
                <strong>Quality:</strong> Subjective sense of feeling rested; also measured objectively by sleep
                fragmentation and efficiency
              </li>
              <li>
                <strong>Timing:</strong> Sleep-wake timing aligned with circadian rhythm and social schedule
              </li>
              <li>
                <strong>Regularity:</strong> Consistent sleep and wake times (variance between weekday and
                weekend sleep should be minimal)
              </li>
              <li>
                <strong>Alertness:</strong> How you feel during the day; daytime sleepiness suggests inadequate
                sleep
              </li>
            </ul>
            <p>
              The simulator measures all these dimensions to give you a holistic view of your sleep health. A
              single score above 85 indicates optimized sleep across all dimensions.
            </p>
          </div>
        </ScienceSection>

        <ScienceSection icon="assessment" title="How This Research Applies to You">
          <div className="science-text">
            <p>
              The Sleep Score Simulator uses a pathway-based model incorporating findings from major sleep
              research, particularly:
            </p>
            <ul className="science-list">
              <li>
                <strong>Chrononutrition research</strong> (Kim et al., 2024): How meal timing affects 5
                dimensions of sleep health
              </li>
              <li>
                <strong>Caffeine-alcohol interaction studies</strong> (Song & Walker, 2023): Real-world effects
                on sleep quantity and quality
              </li>
              <li>
                <strong>Circadian rhythm science:</strong> How light, meal timing, and activity timing synchronize
                your internal clock
              </li>
            </ul>
            <p>
              <strong>Using the simulator effectively:</strong>
            </p>
            <ul className="science-list">
              <li>Adjust one variable at a time to see its isolated impact</li>
              <li>Look for the combination that maximizes your predicted score</li>
              <li>Test your personalized recommendations in real life and compare predictions to actual sleep</li>
              <li>Track changes in HRV and RHR as indicators of recovery improvement</li>
            </ul>
            <p>
              Remember: the simulator provides evidence-based predictions, but individual responses vary. Some
              people are more caffeine-sensitive; others are affected more by light or meal timing. The best
              strategy is to experiment with these variables and observe your own patterns.
            </p>
          </div>
        </ScienceSection>
      </main>

      <footer className="science-footer">
        <Link to="/simulator" className="science-cta">
          <span className="material-symbols-outlined">analytics</span>
          Try the Sleep Score Simulator
        </Link>
      </footer>
    </div>
  )
}
