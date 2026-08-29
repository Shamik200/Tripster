import React, { useState, useMemo } from 'react';
import {
  Plane, MapPin, Calendar, DollarSign, Activity, Settings2, Code, Sparkles, Map,
  Hotel, Compass, CheckCircle, Lightbulb, Package, Star, TrendingUp
} from 'lucide-react';

const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

const INTEREST_OPTIONS = ['sightseeing', 'food', 'nature', 'shopping', 'history', 'nightlife'];
const STYLE_OPTIONS = ['budget', 'balanced', 'luxury'];
const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'INR'];

const initialForm = {
  destination: '',
  origin: 'New York',
  budget: 2000,
  currency: 'USD',
  start_date: new Date().toISOString().split('T')[0],
  end_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  interests: ['sightseeing', 'food'],
  travel_style: 'balanced'
};

function fmt(amount, currency) {
  if (amount == null || amount === '') return `${currency} 0`;
  return `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

// Strip **bold** and *italic* markdown from LLM output
function stripMd(text) {
  if (!text) return '';
  return text.replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1').replace(/^#{1,6}\s/gm, '').trim();
}

// Build a relevant image URL using reliable loremflickr + seed fallback
function activityImageUrl(destination, title) {
  const query = encodeURIComponent(`${destination},travel`).toLowerCase();
  const seed = (destination + title).split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return `https://loremflickr.com/400/220/${query}?random=${seed}`;
}

function ActivityImage({ src, alt }) {
  const [error, setError] = useState(false);
  
  if (error) {
    return <div className="card-img-placeholder">🏝️</div>;
  }
  
  return (
    <img 
      src={src} 
      alt={alt} 
      className="card-img" 
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [tripPlan, setTripPlan] = useState(null);

  // Selection states
  const [selectedFlight, setSelectedFlight] = useState(null);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [selectedActivities, setSelectedActivities] = useState({}); // { "dayIndex": [actIdx, ...] }

  // Finalization states
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [finalizedPlan, setFinalizedPlan] = useState(null);
  const [packedItems, setPackedItems] = useState({});

  // ── Computed budget totals ─────────────────────────────────────────────────
  const budgetTotals = useMemo(() => {
    if (!tripPlan) return null;
    const currency = tripPlan.currency;
    const budget = tripPlan.budget;
    const duration = tripPlan.duration_days;

    const flightCost = selectedFlight !== null ? (tripPlan.flights[selectedFlight]?.price || 0) : 0;
    const hotelCost = selectedHotel !== null ? (tripPlan.hotels[selectedHotel]?.price_per_night || 0) * duration : 0;
    const activityCost = Object.entries(selectedActivities).reduce((total, [dIdx, actIndices]) => {
      const day = tripPlan.itinerary[parseInt(dIdx)];
      if (!day) return total;
      return total + actIndices.reduce((sum, aIdx) => {
        const act = day.activities[aIdx];
        return sum + (act ? act.estimated_cost || 0 : 0);
      }, 0);
    }, 0);

    const totalSpent = flightCost + hotelCost + activityCost;
    const remaining = budget - totalSpent;

    return { flightCost, hotelCost, activityCost, totalSpent, remaining, budget, currency };
  }, [tripPlan, selectedFlight, selectedHotel, selectedActivities]);

  // ── Helpers ────────────────────────────────────────────────────────────────
  function updateField(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  function toggleInterest(interest) {
    setForm(prev => {
      const exists = prev.interests.includes(interest);
      return {
        ...prev,
        interests: exists ? prev.interests.filter(i => i !== interest) : [...prev.interests, interest]
      };
    });
  }

  function toggleActivity(dayIdx, actIdx) {
    setSelectedActivities(prev => {
      const dayKey = String(dayIdx);
      const dayActs = prev[dayKey] || [];
      const newActs = dayActs.includes(actIdx)
        ? dayActs.filter(i => i !== actIdx)
        : [...dayActs, actIdx];
      return { ...prev, [dayKey]: newActs };
    });
  }

  function togglePacked(item) {
    setPackedItems(prev => ({ ...prev, [item]: !prev[item] }));
  }

  // ── Plan Generation ────────────────────────────────────────────────────────
  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setTripPlan(null);
    setFinalizedPlan(null);
    setSelectedFlight(null);
    setSelectedHotel(null);
    setSelectedActivities({});
    setPackedItems({});

    if (!form.destination.trim()) { setError('Destination is required.'); return; }
    if (form.interests.length === 0) { setError('Select at least one interest.'); return; }
    if (new Date(form.start_date) > new Date(form.end_date)) { setError('Start date must be before end date.'); return; }

    const payload = {
      destination: form.destination,
      origin: form.origin,
      budget: Number(form.budget),
      currency: form.currency,
      start_date: form.start_date,
      end_date: form.end_date,
      interests: form.interests,
      travel_style: form.travel_style
    };

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || 'Could not generate plan.');
      setTripPlan(data.trip_plan || null);
    } catch (err) {
      setError(err.message || 'Unexpected error while generating plan.');
    } finally {
      setIsLoading(false);
    }
  }

  // ── Finalization ───────────────────────────────────────────────────────────
  async function handleFinalize() {
    if (!tripPlan || selectedFlight === null || selectedHotel === null) return;

    setIsFinalizing(true);
    setFinalizedPlan(null);
    setPackedItems({});

    const payload = {
      trip_plan: tripPlan,
      selected_flight_index: selectedFlight,
      selected_hotel_index: selectedHotel,
      selected_activity_indices: Object.fromEntries(
        Object.entries(selectedActivities).map(([k, v]) => [k, v])
      )
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || 'Could not finalize plan.');
      setFinalizedPlan(data.finalized_plan);
    } catch (err) {
      setError(err.message || 'Unexpected error while finalizing plan.');
    } finally {
      setIsFinalizing(false);
    }
  }

  // ── Render helpers ─────────────────────────────────────────────────────────
  function BudgetBar() {
    if (!budgetTotals) return null;
    const { flightCost, hotelCost, activityCost, totalSpent, remaining, budget, currency } = budgetTotals;
    const isOver = remaining < 0;
    return (
      <div className="budget-bar">
        <div className="budget-bar-item">
          <span className="budget-bar-label">Total Budget</span>
          <span className="budget-bar-value">{fmt(budget, currency)}</span>
        </div>
        <div className="budget-bar-divider" />
        <div className="budget-bar-item">
          <span className="budget-bar-label">✈ Flight</span>
          <span className="budget-bar-value">{fmt(flightCost, currency)}</span>
        </div>
        <div className="budget-bar-item">
          <span className="budget-bar-label">🏨 Hotel</span>
          <span className="budget-bar-value">{fmt(hotelCost, currency)}</span>
        </div>
        <div className="budget-bar-item">
          <span className="budget-bar-label">🎯 Activities</span>
          <span className="budget-bar-value">{fmt(activityCost, currency)}</span>
        </div>
        <div className="budget-bar-divider" />
        <div className="budget-bar-item">
          <span className="budget-bar-label">Total Spent</span>
          <span className="budget-bar-value spent">{fmt(totalSpent, currency)}</span>
        </div>
        <div className="budget-bar-item">
          <span className="budget-bar-label">Remaining</span>
          <span className={`budget-bar-value ${isOver ? 'negative' : 'positive'}`}>{fmt(remaining, currency)}</span>
        </div>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="hero">
        <div className="hero-icon"><Plane size={40} /></div>
        <h1>Plan Your Perfect Trip</h1>
        <p>Tell us your preferences and let our AI create a personalized itinerary with flights, hotels, and daily activities.</p>
      </header>

      <main className="layout">
        {/* ── FORM ────────────────────────────────────────────────── */}
        <section className="panel">
          <h2><Settings2 size={24} style={{ color: 'var(--brand-primary)' }} /> Trip Preferences</h2>
          <form onSubmit={handleSubmit} className="form">
            <label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><MapPin size={16} /> Destination</div>
              <input type="text" value={form.destination} onChange={e => updateField('destination', e.target.value)} placeholder="e.g. Tokyo, Paris, Bali" />
            </label>
            <label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Plane size={16} /> Origin</div>
              <input type="text" value={form.origin} onChange={e => updateField('origin', e.target.value)} placeholder="e.g. New York" />
            </label>

            <div className="row">
              <label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Calendar size={16} /> Start Date</div>
                <input type="date" value={form.start_date} onChange={e => updateField('start_date', e.target.value)} />
              </label>
              <label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Calendar size={16} /> End Date</div>
                <input type="date" value={form.end_date} onChange={e => updateField('end_date', e.target.value)} />
              </label>
            </div>

            <div className="row">
              <label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><DollarSign size={16} /> Budget</div>
                <input type="number" min="0" step="50" value={form.budget} onChange={e => updateField('budget', e.target.value)} />
              </label>
              <label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><DollarSign size={16} /> Currency</div>
                <select value={form.currency} onChange={e => updateField('currency', e.target.value)}>
                  {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Compass size={16} /> Style</div>
                <select value={form.travel_style} onChange={e => updateField('travel_style', e.target.value)}>
                  {STYLE_OPTIONS.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                </select>
              </label>
            </div>

            <fieldset>
              <legend>Interests & Activities</legend>
              <div className="interest-list">
                {INTEREST_OPTIONS.map(interest => (
                  <button type="button" key={interest} className={form.interests.includes(interest) ? 'pill active' : 'pill'} onClick={() => toggleInterest(interest)}>
                    {interest}
                  </button>
                ))}
              </div>
            </fieldset>

            {error && <div className="error">{error}</div>}

            <button className="submit" type="submit" disabled={isLoading}>
              {isLoading ? <><div className="spinner" /> Generating options...</> : <><Sparkles size={20} /> Find Options</>}
            </button>
          </form>
        </section>

        {/* ── API PAYLOAD ─────────────────────────────────────────── */}
        <section className="panel">
          <h2><Code size={24} style={{ color: 'var(--brand-primary)' }} /> API Payload</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>Data sent to AI agents.</p>
          <pre>{JSON.stringify({ destination: form.destination, origin: form.origin, budget: Number(form.budget), currency: form.currency, start_date: form.start_date, end_date: form.end_date, interests: form.interests, travel_style: form.travel_style }, null, 2)}</pre>
        </section>
      </main>

      {/* ── RESULTS PANEL ───────────────────────────────────────────── */}
      <section className="panel result">
        <h2>
          <Map size={24} style={{ color: 'var(--brand-primary)' }} />
          {finalizedPlan ? ' Your Final Travel Plan' : ' Select Your Options'}
        </h2>

        {!tripPlan && !isLoading && !finalizedPlan && (
          <p style={{ color: 'var(--text-secondary)' }}>No options yet. Fill out the form above to generate choices.</p>
        )}
        {isLoading && (
          <p style={{ color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div className="spinner" /> Tripster AI is researching your trip...
          </p>
        )}

        {/* ── SELECTION PHASE ─────────────────────────────────────── */}
        {tripPlan && !finalizedPlan && !isFinalizing && (
          <div>
            <BudgetBar />

            {/* FLIGHTS */}
            <div className="section-heading">
              <Plane size={18} style={{ color: 'var(--brand-secondary)' }} /> Select a Flight
            </div>
            {(!tripPlan.flights || tripPlan.flights.length === 0) && (
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>No flight options available.</p>
            )}
            <div className="card-grid">
              {tripPlan.flights?.map((flight, idx) => {
                const isSelected = selectedFlight === idx;
                return (
                  <div key={idx} className={`card ${isSelected ? 'selected' : ''}`} onClick={() => setSelectedFlight(idx)}>
                    <div className="card-body">
                      <span className={`card-badge ${isSelected ? 'badge-selected' : 'badge-add'}`}>
                        {isSelected ? '✓ Selected Flight' : '+ Select Flight'}
                      </span>
                      <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{flight.airline}</span>
                        {flight.flight_number && (
                          <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-secondary)' }}>
                            {flight.flight_number}
                          </span>
                        )}
                      </div>
                      <div className="card-subtitle">{flight.origin} → {flight.destination}</div>
                      {flight.departure && flight.arrival && (
                        <div className="card-subtitle" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          ⏰ {flight.departure} – {flight.arrival} ({flight.duration})
                        </div>
                      )}
                      <div className="card-subtitle" style={{ fontSize: '12px' }}>
                        {flight.is_direct ? '✈ Direct Non-stop' : '🔄 1 Stop Connecting'}
                      </div>
                      <div className="card-price">{fmt(flight.price, tripPlan.currency)}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* HOTELS */}
            <div className="section-heading">
              <Hotel size={18} style={{ color: 'var(--brand-secondary)' }} /> Select a Hotel
            </div>
            {(!tripPlan.hotels || tripPlan.hotels.length === 0) && (
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>No hotel options available.</p>
            )}
            <div className="card-grid">
              {tripPlan.hotels?.map((hotel, idx) => {
                const isSelected = selectedHotel === idx;
                return (
                  <div key={idx} className={`card ${isSelected ? 'selected' : ''}`} onClick={() => setSelectedHotel(idx)}>
                    <div className="card-body">
                      <span className={`card-badge ${isSelected ? 'badge-selected' : 'badge-add'}`}>
                        {isSelected ? '✓ Selected Hotel' : '+ Select Hotel'}
                      </span>
                      <div className="card-title">{hotel.name}</div>
                      <div className="card-subtitle">📍 {hotel.location}</div>
                      <div className="card-subtitle" style={{ color: '#fbbf24' }}>
                        {'★'.repeat(Math.round(hotel.rating || 4))} <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>({hotel.rating}/5)</span>
                      </div>
                      <div className="card-price">{fmt(hotel.price_per_night, tripPlan.currency)} / night</div>
                      {isSelected && (
                        <div style={{ fontSize: '12px', color: '#34d399', marginTop: '2px', fontWeight: 600 }}>
                          Total: {fmt(hotel.price_per_night * tripPlan.duration_days, tripPlan.currency)} ({tripPlan.duration_days} nights)
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* ACTIVITIES BY DAY */}
            <div className="section-heading">
              <Activity size={18} style={{ color: 'var(--brand-secondary)' }} /> Select Activities by Day
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px', marginTop: '-8px' }}>
              Hotel check-in on Day 1 and check-out on the last day are automatic. Select the experiences you want!
            </p>
            {tripPlan.itinerary?.map((day, dIdx) => (
              <div key={day.day} style={{ marginBottom: '28px' }}>
                <h5 style={{ fontSize: '15px', marginBottom: '12px', color: 'var(--text-primary)', opacity: 0.9 }}>
                  Day {day.day} — {day.title}
                </h5>
                <div className="card-grid">
                  {day.activities.map((act, aIdx) => {
                    const dayKey = String(dIdx);
                    const isSelected = (selectedActivities[dayKey] || []).includes(aIdx);
                    const imgSrc = activityImageUrl(tripPlan.destination, act.title);
                    return (
                      <div key={aIdx} className={`card ${isSelected ? 'selected' : ''}`} onClick={() => toggleActivity(dIdx, aIdx)}>
                        <ActivityImage src={imgSrc} alt={act.title} />
                        <div className="card-body">
                          <span className={`card-badge ${isSelected ? 'badge-selected' : 'badge-add'}`}>
                            {isSelected ? '✓ Selected — tap to remove' : '+ Add to plan'}
                          </span>
                          <div className="card-title">{act.title}</div>
                          <div className="card-price">{fmt(act.estimated_cost, tripPlan.currency)}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {/* FINALIZE BUTTON */}
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '24px', marginTop: '8px' }}>
              <BudgetBar />
              <button
                className="submit"
                onClick={handleFinalize}
                disabled={selectedFlight === null || selectedHotel === null}
                style={{ maxWidth: '340px' }}
              >
                <CheckCircle size={20} /> Generate Final Plan with AI
              </button>
              {(selectedFlight === null || selectedHotel === null) && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '10px' }}>
                  Please select at least a flight and a hotel to proceed.
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── FINALIZING LOADER ─────────────────────────────────── */}
        {isFinalizing && (
          <div className="finalizing-overlay">
            <div className="finalizing-spinner" />
            <span>AI is crafting your personalized travel plan...</span>
          </div>
        )}

        {/* ── FINALIZED PLAN ────────────────────────────────────── */}
        {finalizedPlan && tripPlan && (
          <div>
            {/* Header */}
            <h3 style={{ fontSize: '26px', fontWeight: '800', marginBottom: '6px' }}>
              {tripPlan.destination}
            </h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
              {tripPlan.start_date} → {tripPlan.end_date} &nbsp;·&nbsp; {tripPlan.duration_days} nights
            </p>

            {/* Budget summary */}
            <div className="budget-bar" style={{ position: 'static', marginBottom: '28px' }}>
              <div className="budget-bar-item">
                <span className="budget-bar-label">Total Budget</span>
                <span className="budget-bar-value">{fmt(tripPlan.budget, tripPlan.currency)}</span>
              </div>
              <div className="budget-bar-divider" />
              <div className="budget-bar-item">
                <span className="budget-bar-label">Total Spent</span>
                <span className="budget-bar-value spent">{fmt(finalizedPlan.total_spent, tripPlan.currency)}</span>
              </div>
              <div className="budget-bar-item">
                <span className="budget-bar-label">Budget Remaining</span>
                <span className={`budget-bar-value ${finalizedPlan.budget_remaining < 0 ? 'negative' : 'positive'}`}>
                  {fmt(finalizedPlan.budget_remaining, tripPlan.currency)}
                </span>
              </div>
            </div>

            {/* Narrative */}
            <div className="section-heading">
              <Star size={18} style={{ color: 'var(--brand-secondary)' }} /> Trip Overview
            </div>
            <div className="narrative">{stripMd(finalizedPlan.narrative_summary)}</div>

            {/* Chosen Flight */}
            <div className="section-heading">
              <Plane size={18} style={{ color: 'var(--brand-secondary)' }} /> Your Flight
            </div>
            <div className="summary-card">
              <div className="summary-card-info">
                <div className="summary-card-title">{tripPlan.flights[selectedFlight].airline}</div>
                <div className="summary-card-sub">
                  {tripPlan.flights[selectedFlight].origin} → {tripPlan.flights[selectedFlight].destination}
                  &nbsp;·&nbsp; {tripPlan.flights[selectedFlight].duration}
                  &nbsp;·&nbsp; {tripPlan.flights[selectedFlight].is_direct ? 'Direct' : 'With stop'}
                </div>
              </div>
              <div className="summary-card-price">{fmt(tripPlan.flights[selectedFlight].price, tripPlan.currency)}</div>
            </div>

            {/* Chosen Hotel */}
            <div className="section-heading">
              <Hotel size={18} style={{ color: 'var(--brand-secondary)' }} /> Your Hotel
            </div>
            <div className="summary-card">
              <div className="summary-card-info">
                <div className="summary-card-title">{tripPlan.hotels[selectedHotel].name}</div>
                <div className="summary-card-sub">
                  {tripPlan.hotels[selectedHotel].location}
                  &nbsp;·&nbsp; {'★'.repeat(Math.round(tripPlan.hotels[selectedHotel].rating))} {tripPlan.hotels[selectedHotel].rating}/5
                </div>
              </div>
              <div className="summary-card-price">
                {fmt(tripPlan.hotels[selectedHotel].price_per_night * tripPlan.duration_days, tripPlan.currency)}
                <div style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-secondary)', textAlign: 'right' }}>
                  {fmt(tripPlan.hotels[selectedHotel].price_per_night, tripPlan.currency)}/night
                </div>
              </div>
            </div>

            {/* Day-by-day */}
            <div className="section-heading">
              <Activity size={18} style={{ color: 'var(--brand-secondary)' }} /> Your Itinerary
            </div>
            <div className="day-prose">{stripMd(finalizedPlan.day_by_day)}</div>

            {/* Suggestions */}
            {finalizedPlan.suggestions?.length > 0 && (
              <>
                <div className="section-heading">
                  <Lightbulb size={18} style={{ color: 'var(--brand-secondary)' }} /> Travel Tips & Suggestions
                </div>
                <div className="suggestions-grid">
                  {finalizedPlan.suggestions.map((tip, i) => (
                    <div key={i} className="suggestion-card">
                      <span className="suggestion-icon"><TrendingUp size={14} /></span>
                      <span>{tip}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Packing List */}
            {finalizedPlan.packing_list?.length > 0 && (
              <>
                <div className="section-heading">
                  <Package size={18} style={{ color: 'var(--brand-secondary)' }} /> Packing Checklist
                  <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: 'auto' }}>
                    Click items to check them off
                  </span>
                </div>
                <ul className="packing-list">
                  {finalizedPlan.packing_list.map(item => (
                    <li key={item} className={`packing-item ${packedItems[item] ? 'packed' : ''}`} onClick={() => togglePacked(item)}>
                      <div className="packing-checkbox">{packedItems[item] ? '✓' : ''}</div>
                      {item}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default App;
