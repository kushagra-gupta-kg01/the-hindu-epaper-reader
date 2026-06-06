// ==========================================================================
   // GLOBAL STATE & STATE SELECTORS
   // ==========================================================================

const state = {
  date: null,          // YYYY-MM-DD format
  city: 'th_delhi',    // e.g. th_delhi
  issueId: null,       // e.g. GKLG1M8C9.1
  rawPages: [],        // Raw layout pages from API
  theme: 'theme-broadside',
  activeArticleRef: null,
  isArticleLoading: false,
  savedScrollY: 0,
  focusTrigger: null,
  topPicks: [],
  topPicksStatus: 'not_generated',
  limit: 10,
  bionicReading: false,
  fixationPoint: 3,
  activeArticleData: null,
  paperStyle: 'paper-ivory'
};

// ==========================================================================
// TELEMETRY & ERROR TRACKING PROXIES
// ==========================================================================

function captureException(error) {
  if (typeof Sentry !== 'undefined' && Sentry.captureException) {
    Sentry.captureException(error);
  } else {
    console.error("Blocked/Fallback captureException:", error);
  }
}

function logInteraction(eventName, details = {}) {
  if (typeof Sentry !== 'undefined' && Sentry.addBreadcrumb) {
    Sentry.addBreadcrumb({
      category: 'ui',
      message: eventName,
      data: details,
      level: 'info'
    });
  }
  console.log(`[Interaction] ${eventName}`, details);
}

if (typeof window !== 'undefined') {
  window.captureException = captureException;
  window.logInteraction = logInteraction;
}

// DOM Elements
const dateSelect = document.getElementById('date-select');
const citySelect = document.getElementById('city-select');
const notificationBanner = document.getElementById('notification-banner');
const notificationText = document.getElementById('notification-text');
const notificationActionBtn = document.getElementById('notification-action-btn');
const sectionNavList = document.getElementById('section-nav-list');
const headlinesContent = document.getElementById('headlines-content');
const mainLoader = document.getElementById('main-loader');
const readerPane = document.getElementById('reader-pane');
const readerProgressBar = document.getElementById('reader-progress-bar');
const readerCloseBtn = document.getElementById('reader-close-btn');
const readerContent = document.getElementById('reader-content');
const readerLoader = document.getElementById('reader-loader');

const readerCategory = document.getElementById('reader-category');
const readerHeadline = document.getElementById('reader-headline');
const readerByline = document.getElementById('reader-byline');
const readerDateline = document.getElementById('reader-dateline');
const readerBody = document.getElementById('reader-body');

const aiPicksSection = document.getElementById('ai-picks-section');
const aiStatusBadge = document.getElementById('ai-status-badge');
const aiTriggerPanel = document.getElementById('ai-trigger-panel');
const aiLoadingPanel = document.getElementById('ai-loading-panel');
const aiReadyPanel = document.getElementById('ai-ready-panel');
const aiPicksGrid = document.getElementById('ai-picks-grid');
const aiGenerateBtn = document.getElementById('ai-generate-btn');
const aiLimitBtns = document.querySelectorAll('#ai-limit-group .ai-limit-btn');

const bionicToggleBtn = document.getElementById('bionic-toggle-btn');
const bionicFixationSelect = document.getElementById('bionic-fixation-select');
const fixationControl = document.getElementById('fixation-control');

// ==========================================================================
// UTILITY FUNCTIONS
// ==========================================================================

// Map raw section names to clean display categories
function getCleanSectionName(rawName) {
  if (!rawName) return "General";
  const name = rawName.toLowerCase();
  if (name.includes("front") || name.includes("jacket")) return "Front Page";
  if (name.includes("regional") || name.includes("rgladpage")) return "Regional";
  if (name.includes("states") || name.includes("south")) return "States";
  if (name.includes("edit")) return "Editorial";
  if (name.includes("text")) return "Text & Context";
  if (name.includes("news")) return "News";
  if (name.includes("business")) return "Business";
  if (name.includes("foreign") || name.includes("world")) return "World";
  if (name.includes("sport") || name.includes("back")) return "Sports";
  if (name.includes("science")) return "Science";
  return "General";
}

// Filter out system placeholders and non-article elements
const noiseHeadlines = [
  "th_subscribe_qr_code_new", "th27 panel", "nearby_shape_new", "sudoku",
  "sudoku_solution", "know your english", "the daily quiz", "the science quiz",
  "rgladpage", "text_feedback", "scoreboard", "the results", "live telecast"
];

function isNoiseArticle(headline) {
  if (!headline) return true;
  const h = headline.toLowerCase().trim();
  if (noiseHeadlines.includes(h)) return true;
  if (h.startsWith("th27 promo") || h.startsWith("th27 nearby") || h.startsWith("news in numbers")) return true;
  if (h.startsWith("promo")) return true;
  if (/^\d+bg/.test(h)) return true; // Matches e.g. "23bg..."
  if (h.includes("page1") || h.includes("sirpage") || h.includes("stadiump-age")) return true;
  if (/^\d+$/.test(h)) return true; // Matches pure page markers e.g. "14805"
  return false;
}

// Escape HTML special characters to prevent XSS
function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Synchronize Bionic Reading UI options panel
function syncBionicUI() {
  if (bionicToggleBtn) {
    bionicToggleBtn.textContent = state.bionicReading ? "Bionic: On" : "Bionic: Off";
    if (state.bionicReading) {
      bionicToggleBtn.classList.add('active');
      document.documentElement.classList.add('bionic-active');
    } else {
      bionicToggleBtn.classList.remove('active');
      document.documentElement.classList.remove('bionic-active');
    }
  }
  if (fixationControl) {
    fixationControl.style.display = state.bionicReading ? 'inline-block' : 'none';
  }
  if (bionicFixationSelect) {
    bionicFixationSelect.value = state.fixationPoint;
  }
}

// Parse URL query parameters
function parseQueryParams(queryString) {
  const params = { date: null, city: null, article: null };
  if (!queryString) return params;
  
  const searchParams = new URLSearchParams(queryString);
  const date = searchParams.get('date');
  const city = searchParams.get('city');
  const article = searchParams.get('article');
  
  // Validate YYYY-MM-DD date format
  if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
    params.date = date;
  }
  if (city) {
    params.city = city;
  }
  if (article) {
    params.article = article;
  }
  
  // If date or city is invalid, return null for both to trigger defaults
  if (!params.date || !params.city) {
    return { date: null, city: null, article: params.article };
  }
  
  return params;
}

// Get current date formatted in Indian Standard Time (IST)
function getTodayIST() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  return formatter.format(new Date());
}

// Calculate yesterday's date relative to a date string YYYY-MM-DD
function getYesterdayDate(dateStr) {
  const d = new Date(dateStr);
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
}

// ==========================================================================
// APP LIFE CYCLE & STATE MANAGEMENT
// ==========================================================================

// Startup guard to allow test execution without running main app logic
document.addEventListener('DOMContentLoaded', () => {
  if (window.__TEST_MODE__) return;
  initApp();
});

function initApp() {
  // 1. Setup Date Picker constraints (future block using IST)
  const todayIST = getTodayIST();
  dateSelect.max = todayIST;

  // 2. Load preferences / Parse URL parameters
  const urlParams = parseQueryParams(window.location.search);
  
  state.theme = localStorage.getItem('the-hindu-reader-theme') || 'theme-broadside';
  state.paperStyle = localStorage.getItem('the-hindu-reader-paper') || 'paper-ivory';
  
  // Load Bionic preferences: default to true on Gutenberg if no saved override exists
  const storedBionic = localStorage.getItem('bionic-enabled');
  if (storedBionic !== null) {
    state.bionicReading = storedBionic === 'true';
  } else {
    state.bionicReading = (state.theme === 'theme-gutenberg');
  }
  
  applyTheme(state.theme);
  
  // Update state with URL parameters or fallback preferences
  state.date = urlParams.date || todayIST;
  state.city = urlParams.city || localStorage.getItem('the-hindu-reader-city') || 'th_delhi';
  
  state.fixationPoint = parseInt(localStorage.getItem('bionic-fixation'), 10) || 3;
  syncBionicUI();
  
  // Sync state to DOM controls
  dateSelect.value = state.date;
  citySelect.value = state.city;

  // 3. Event Listeners for controls
  dateSelect.addEventListener('change', () => {
    // Empty Date Input Fallback
    if (!dateSelect.value) {
      dateSelect.value = getTodayIST();
    }
    updateState({ date: dateSelect.value });
  });

  citySelect.addEventListener('change', () => {
    updateState({ city: citySelect.value });
    localStorage.setItem('the-hindu-reader-city', citySelect.value);
  });

  // Theme Switcher Buttons
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const selectedTheme = btn.getAttribute('data-theme');
      if (selectedTheme) {
        // When switching to Gutenberg, if no explicit override is stored, default bionic to true
        if (selectedTheme === 'theme-gutenberg' && localStorage.getItem('bionic-enabled') === null) {
          state.bionicReading = true;
          syncBionicUI();
        }
        updateState({ theme: selectedTheme });
      }
    });
  });

  // Gutenberg Paper Selector Click Bindings
  document.querySelectorAll('#paper-style-selector .ctrl-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const selectedPaper = btn.getAttribute('data-paper');
      if (selectedPaper) {
        logInteraction("paper_style_changed", { paper: selectedPaper });
        state.paperStyle = selectedPaper;
        localStorage.setItem('the-hindu-reader-paper', selectedPaper);
        
        // Update document classes whitelisting
        const allPapers = ['paper-ivory', 'paper-white', 'paper-sepia'];
        allPapers.forEach(p => document.documentElement.classList.remove(p));
        document.documentElement.classList.add(selectedPaper);
        
        syncPaperUI();
      }
    });
  });

  // Reader Close Action
  readerCloseBtn.addEventListener('click', () => {
    closeArticleReader();
  });

  // Bionic Reading Options Binding
  if (bionicToggleBtn) {
    bionicToggleBtn.addEventListener('click', () => {
      state.bionicReading = !state.bionicReading;
      localStorage.setItem('bionic-enabled', state.bionicReading);
      logInteraction("bionic_toggled", { enabled: state.bionicReading });
      syncBionicUI();
      renderArticleContent();
    });
  }

  if (bionicFixationSelect) {
    bionicFixationSelect.addEventListener('change', () => {
      state.fixationPoint = parseInt(bionicFixationSelect.value, 10) || 3;
      localStorage.setItem('bionic-fixation', state.fixationPoint);
      logInteraction("bionic_fixation_changed", { fixation: state.fixationPoint });
      renderArticleContent();
    });
  }

  // AI picks generation trigger
  if (aiGenerateBtn) {
    aiGenerateBtn.addEventListener('click', () => {
      generateTopPicks();
    });
  }

  // AI picks count limit selector click handlers
  if (aiLimitBtns && aiLimitBtns.length > 0) {
    aiLimitBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        aiLimitBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.limit = parseInt(btn.getAttribute('data-limit'), 10) || 10;
        if (state.topPicksStatus === 'ready') {
          renderTopPicksGrid();
        }
      });
    });
  }

  // Browser Back/Forward Sync (popstate)
  window.addEventListener('popstate', (e) => {
    const freshParams = parseQueryParams(window.location.search);
    
    // Update selectors if changed
    if (freshParams.date && freshParams.city) {
      const dateChanged = freshParams.date !== state.date;
      const cityChanged = freshParams.city !== state.city;
      
      state.date = freshParams.date;
      state.city = freshParams.city;
      dateSelect.value = state.date;
      citySelect.value = state.city;
      
      if (dateChanged || cityChanged) {
        fetchHeadlines();
      }
    }
    
    // Update article state
    if (freshParams.article) {
      if (freshParams.article !== state.activeArticleRef) {
        openArticleReader(freshParams.article);
      }
    } else {
      if (state.activeArticleRef) {
        // Close reader silently (don't push another state since popstate already did)
        closeArticleReader(false);
      }
    }
  });

  // 4. Initial Fetch
  fetchHeadlines().then(() => {
    // If URL contains an article on load, open it immediately
    if (urlParams.article) {
      openArticleReader(urlParams.article);
    }
  });
}

// Global state update wrapper
function updateState(newState) {
  const dateChanged = newState.date !== undefined && newState.date !== state.date;
  const cityChanged = newState.city !== undefined && newState.city !== state.city;
  const themeChanged = newState.theme !== undefined && newState.theme !== state.theme;

  Object.assign(state, newState);

  if (themeChanged) {
    applyTheme(state.theme);
  }

  // Push URL History Update on query state changes
  if (dateChanged || cityChanged) {
    syncUrlHistory();
    fetchHeadlines();
  }
}

// Sync current state to URL Query Parameters
function syncUrlHistory() {
  const query = new URLSearchParams();
  query.set('date', state.date);
  query.set('city', state.city);
  if (state.activeArticleRef) {
    query.set('article', state.activeArticleRef);
  }
  
  const newUrl = `${window.location.pathname}?${query.toString()}`;
  window.history.pushState(null, '', newUrl);
}

// Apply the theme class to HTML root
function applyTheme(themeClass) {
  logInteraction("theme_changed", { theme: themeClass });
  const allThemes = ['theme-broadside', 'theme-folio', 'theme-dispatch', 'theme-gutenberg'];
  allThemes.forEach(t => document.documentElement.classList.remove(t));
  document.documentElement.classList.add(themeClass);
  
  const allPapers = ['paper-ivory', 'paper-white', 'paper-sepia'];
  allPapers.forEach(p => document.documentElement.classList.remove(p));
  
  const subcontrols = document.getElementById('gutenberg-subcontrols');
  if (themeClass === 'theme-gutenberg') {
    document.documentElement.classList.add(state.paperStyle || 'paper-ivory');
    if (subcontrols) {
      subcontrols.style.display = 'flex';
    }
    syncPaperUI();
  } else {
    if (subcontrols) {
      subcontrols.style.display = 'none';
    }
  }

  // Update button active state
  document.querySelectorAll('.theme-btn').forEach(btn => {
    const themeAttr = btn.getAttribute('data-theme');
    if (themeAttr) {
      if (themeAttr === themeClass) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });
  localStorage.setItem('the-hindu-reader-theme', themeClass);
}

// Synchronize Gutenberg sub-paper active classes on buttons
function syncPaperUI() {
  const paperBtns = document.querySelectorAll('#gutenberg-subcontrols .ctrl-btn');
  paperBtns.forEach(btn => {
    const paperAttr = btn.getAttribute('data-paper');
    if (paperAttr) {
      if (paperAttr === state.paperStyle) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });
}

// Display Warning Banner
function showBanner(message, actionLabel = null, actionFn = null) {
  notificationText.textContent = message;
  notificationBanner.style.display = 'flex';
  
  if (actionLabel && actionFn) {
    notificationActionBtn.textContent = actionLabel;
    notificationActionBtn.style.display = 'inline-block';
    // Clear previous event listeners
    const newBtn = notificationActionBtn.cloneNode(true);
    notificationActionBtn.parentNode.replaceChild(newBtn, notificationActionBtn);
    newBtn.addEventListener('click', () => {
      actionFn();
      hideBanner();
    });
  } else {
    notificationActionBtn.style.display = 'none';
  }
}

function hideBanner() {
  notificationBanner.style.display = 'none';
}

// ==========================================================================
// DATA FETCHING & RENDERING PIPELINE
// ==========================================================================

async function fetchHeadlines() {
  hideBanner();
  mainLoader.style.display = 'flex';
  headlinesContent.style.display = 'none';
  sectionNavList.innerHTML = '';
  
  // Hide picks section immediately to prevent stale visual flashes
  if (aiPicksSection) {
    aiPicksSection.style.display = 'none';
  }
  
  try {
    const response = await fetch(`/api/headlines?date=${state.date}&city=${state.city}`);
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const detail = errData.detail || "Server error";
      
      // Handle unpublished editions fallback
      if ((response.status === 502 || response.status === 400) && state.date === getTodayIST()) {
        const yesterday = getYesterdayDate(state.date);
        showBanner(
          `Today's edition (${state.date}) is not published yet.`,
          `Read yesterday's paper`,
          () => {
            dateSelect.value = yesterday;
            updateState({ date: yesterday });
          }
        );
      } else {
        showBanner(`Error: ${detail}`);
      }
      
      mainLoader.style.display = 'none';
      return;
    }

    const data = await response.json();
    state.issueId = data.issue_id;
    state.rawPages = data.pages || [];
    
    renderGrid();
    
    // Check Top Picks Cache if we have articles loaded
    if (state.rawPages && state.rawPages.length > 0) {
      checkTopPicksCache(state.date, state.city);
    }
  } catch (error) {
    captureException(error);
    showBanner(`Network error: Unable to connect to server.`);
    mainLoader.style.display = 'none';
  }
}

function renderGrid() {
  headlinesContent.innerHTML = '';
  sectionNavList.innerHTML = '';
  
  if (!state.rawPages || state.rawPages.length === 0) {
    renderEmptyState();
    mainLoader.style.display = 'none';
    return;
  }

  // 1. Group articles by clean categories
  const sectionsMap = {}; // categoryName -> list of articles
  
  state.rawPages.forEach(page => {
    const category = getCleanSectionName(page.page_name);
    
    if (!sectionsMap[category]) {
      sectionsMap[category] = [];
    }
    
    page.articles.forEach(art => {
      // Noise Filter Check
      if (isNoiseArticle(art.headline)) {
        return;
      }
      
      // Add article references
      sectionsMap[category].push({
        ...art,
        page_num: page.page_num,
        page_name: page.page_name
      });
    });
  });

  // Filter out categories with zero active articles
  const activeSections = Object.keys(sectionsMap).filter(cat => sectionsMap[cat].length > 0);
  
  if (activeSections.length === 0) {
    renderEmptyState(true); // Empty due to filter
    mainLoader.style.display = 'none';
    return;
  }

  // 2. Render Sticky Navigation Links & Section Layouts
  activeSections.forEach((category, idx) => {
    const safeId = `section-${category.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
    
    // Add Nav Link
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.className = 'section-nav-link';
    if (idx === 0) a.classList.add('active');
    a.textContent = category;
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const targetBlock = document.getElementById(safeId);
      if (targetBlock) {
        targetBlock.scrollIntoView({ behavior: 'smooth' });
      }
    });
    li.appendChild(a);
    sectionNavList.appendChild(li);

    // Create Section Layout Container
    const sectionBlock = document.createElement('section');
    sectionBlock.id = safeId;
    sectionBlock.className = 'section-block';

    const header = document.createElement('h2');
    header.className = 'section-header';
    header.textContent = category;
    
    sectionBlock.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'article-grid';

    // 3. Render Cards (First article spans as lead card)
    const articles = sectionsMap[category];
    articles.forEach((art, artIdx) => {
      const card = document.createElement('article');
      card.className = 'article-card';
      // Lead story formatting
      if (artIdx === 0 && articles.length > 1) {
        card.classList.add('lead');
      }

      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `Read article: ${art.headline}`);
      
      // Prevent XSS using textContent
      const cardInner = document.createElement('div');
      
      const meta = document.createElement('div');
      meta.className = 'card-meta';
      meta.textContent = art.page_name.replace('_', ' ');
      cardInner.appendChild(meta);

      const headline = document.createElement('h3');
      headline.className = 'card-headline';
      headline.textContent = art.headline;
      cardInner.appendChild(headline);

      card.appendChild(cardInner);

      const footer = document.createElement('div');
      footer.className = 'card-footer';
      
      const pageInfo = document.createElement('span');
      pageInfo.textContent = `Page ${art.page_num}`;
      footer.appendChild(pageInfo);

      const clickToRead = document.createElement('span');
      clickToRead.style.fontWeight = '700';
      clickToRead.textContent = 'Read Text →';
      footer.appendChild(clickToRead);

      card.appendChild(footer);

      // Card click events
      card.addEventListener('click', () => {
        openArticleReader(art.html_ref);
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openArticleReader(art.html_ref);
        }
      });

      grid.appendChild(card);
    });

    sectionBlock.appendChild(grid);
    headlinesContent.appendChild(sectionBlock);
  });

  // 4. Setup scroll tracking for navigation links active highlight
  setupScrollObserver();

  mainLoader.style.display = 'none';
  headlinesContent.style.display = 'block';
}

// Render Empty/Filtered State
function renderEmptyState(filtered = false) {
  const div = document.createElement('div');
  div.className = 'empty-state';
  
  const title = document.createElement('h3');
  title.className = 'empty-state-title';
  title.textContent = filtered ? "Filter Result Empty" : "No Edition Loaded";
  div.appendChild(title);

  const desc = document.createElement('p');
  desc.className = 'empty-state-desc';
  desc.textContent = filtered 
    ? "All layouts in this edition consist of advertisements or system QR codes that were filtered out."
    : "Select another date or city edition above to read headlines.";
  div.appendChild(desc);



  headlinesContent.appendChild(div);
}

// Active Nav highlight scroll spy (IntersectionObserver)
function setupScrollObserver() {
  const sections = document.querySelectorAll('.section-block');
  const navLinks = document.querySelectorAll('.section-nav-link');
  
  if (sections.length === 0 || navLinks.length === 0) return;

  const observerOptions = {
    root: null,
    rootMargin: '-10% 0px -80% 0px', // Triggers when section enters the upper 20% viewport area
    threshold: 0
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        navLinks.forEach(link => {
          // Compare target text or rebuild id
          const targetCategory = entry.target.querySelector('.section-header').firstChild.textContent.trim();
          if (link.textContent === targetCategory) {
            link.classList.add('active');
            
            // Scroll nav link into view horizontally if overflowed
            link.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
          } else {
            link.classList.remove('active');
          }
        });
      }
    });
  }, observerOptions);

  sections.forEach(sec => observer.observe(sec));
}

// ==========================================================================
// AI EDITOR'S PICKS WIDGET & RENDER PIPELINE
// ==========================================================================

function switchPanelState(stateName) {
  if (stateName === 'trigger') {
    aiTriggerPanel.style.display = 'block';
    aiLoadingPanel.style.display = 'none';
    aiReadyPanel.style.display = 'none';
    aiStatusBadge.textContent = 'Ready to generate';
  } else if (stateName === 'loading') {
    aiTriggerPanel.style.display = 'none';
    aiLoadingPanel.style.display = 'block';
    aiReadyPanel.style.display = 'none';
    aiStatusBadge.textContent = 'Analyzing headlines...';
  } else if (stateName === 'ready') {
    aiTriggerPanel.style.display = 'none';
    aiLoadingPanel.style.display = 'none';
    aiReadyPanel.style.display = 'block';
    aiStatusBadge.textContent = 'Curated by AI Editor';
  }
}

function renderTopPicksGrid() {
  aiPicksGrid.innerHTML = '';
  if (!state.topPicks || state.topPicks.length === 0) return;

  const slicedPicks = state.topPicks.slice(0, state.limit);
  slicedPicks.forEach((art, index) => {
    const rank = index + 1;
    const ratings = art.ratings || {};
    const impact = ratings.impact || 0;
    const importance = ratings.importance || 0;
    const interest = ratings.interest || 0;
    const depth = ratings.depth || 0;
    const avgScore = (impact + importance + interest + depth) / 4;

    const card = document.createElement('div');
    card.className = 'ai-card';
    card.setAttribute('tabindex', '0');
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Read AI Pick #${rank}: ${art.headline || 'Untitled'}`);

    // Card Top Section (Rank and Source Page Meta)
    const cardTop = document.createElement('div');
    cardTop.className = 'card-top';

    const rankBadge = document.createElement('span');
    rankBadge.className = 'card-badge';
    rankBadge.textContent = `#${rank}`;
    cardTop.appendChild(rankBadge);

    const scoreMeta = document.createElement('span');
    scoreMeta.className = 'card-meta';
    scoreMeta.textContent = `Score: ${avgScore.toFixed(1)}/10`;
    cardTop.appendChild(scoreMeta);

    card.appendChild(cardTop);

    // Headline
    const headline = document.createElement('h3');
    headline.className = 'card-headline';
    headline.textContent = art.headline || 'Untitled Article';
    card.appendChild(headline);

    // AI Reason / Summary
    if (art.reason) {
      const reason = document.createElement('p');
      reason.className = 'card-reason';
      reason.textContent = art.reason;
      card.appendChild(reason);
    }

    // Individual Sub-ratings Pill Container
    const ratingsContainer = document.createElement('div');
    ratingsContainer.className = 'card-ratings';

    const tags = [
      { label: 'IMP', val: impact },
      { label: 'SIG', val: importance },
      { label: 'INT', val: interest },
      { label: 'DEP', val: depth }
    ];

    tags.forEach(t => {
      const tag = document.createElement('span');
      tag.className = 'score-tag';
      tag.textContent = `${t.label}: ${t.val}`;
      ratingsContainer.appendChild(tag);
    });

    card.appendChild(ratingsContainer);

    // Click handler to launch reader
    card.addEventListener('click', () => {
      if (art.html_ref) {
        openArticleReader(art.html_ref);
      }
    });

    card.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && art.html_ref) {
        e.preventDefault();
        openArticleReader(art.html_ref);
      }
    });

    aiPicksGrid.appendChild(card);
  });
}

async function checkTopPicksCache(date, city) {
  const requestDate = date;
  const requestCity = city;

  try {
    const response = await fetch(`/api/top-headlines?date=${date}&city=${city}&generate=false`);
    
    // Race-condition check
    if (state.date !== requestDate || state.city !== requestCity) {
      return;
    }

    if (!response.ok) {
      state.topPicksStatus = 'failed';
      switchPanelState('trigger');
      aiPicksSection.style.display = 'none';
      return;
    }

    const data = await response.json();
    
    // Race-condition check
    if (state.date !== requestDate || state.city !== requestCity) {
      return;
    }

    if (data.status === 'ready') {
      state.topPicksStatus = 'ready';
      state.topPicks = data.top_articles || [];
      renderTopPicksGrid();
      switchPanelState('ready');
      aiPicksSection.style.display = 'block';
    } else {
      state.topPicksStatus = 'not_generated';
      state.topPicks = [];
      switchPanelState('trigger');
      aiPicksSection.style.display = 'block';
    }
  } catch (error) {
    captureException(error);
    console.error("Error checking top picks cache:", error);
    if (state.date === requestDate && state.city === requestCity) {
      aiPicksSection.style.display = 'none';
    }
  }
}

async function generateTopPicks() {
  const requestDate = state.date;
  const requestCity = state.city;

  switchPanelState('loading');
  aiPicksSection.style.display = 'block';

  try {
    const response = await fetch(`/api/top-headlines?date=${requestDate}&city=${requestCity}&generate=true`);
    
    // Race-condition check
    if (state.date !== requestDate || state.city !== requestCity) {
      return;
    }

    if (!response.ok) {
      throw new Error("API call failed");
    }

    const data = await response.json();
    
    // Race-condition check
    if (state.date !== requestDate || state.city !== requestCity) {
      return;
    }

    if (data.status === 'ready') {
      state.topPicksStatus = 'ready';
      state.topPicks = data.top_articles || [];
      renderTopPicksGrid();
      switchPanelState('ready');
    } else {
      throw new Error("Data not ready");
    }
  } catch (error) {
    captureException(error);
    console.error("Error generating top picks:", error);
    if (state.date === requestDate && state.city === requestCity) {
      state.topPicksStatus = 'failed';
      switchPanelState('trigger');
      showBanner("Not able to generate AI picks right now");
    }
  }
}

// ==========================================================================
// DISTRACTION-FREE OVERLAY READER ACTION
// ==========================================================================

async function openArticleReader(htmlRef) {
  if (state.isArticleLoading) return;
  state.isArticleLoading = true;
  state.activeArticleRef = htmlRef;

  // Reset scroll coordinates of reader pane to zero (Gap 6 fix)
  readerPane.scrollTop = 0;

  // Sync URL history state
  syncUrlHistory();

  // Save keyboard trigger element for focus restoration
  state.focusTrigger = document.activeElement;

  // Viewport scroll coordinate lock (preserves scroll on iOS)
  state.savedScrollY = window.scrollY;
  document.body.classList.add('reader-open');
  document.body.style.top = `-${state.savedScrollY}px`;

  // Display overlay
  readerPane.style.display = 'block';
  readerPane.focus();
  readerProgressBar.style.width = '0%';
  readerLoader.style.display = 'flex';
  readerContent.style.display = 'none';

  // Global listeners activation
  window.addEventListener('keydown', handleEscapeKey);
  readerPane.addEventListener('scroll', handleReaderProgress);

  try {
    const response = await fetch(`/api/article?city=${state.city}&issue_id=${state.issueId}&ref=${encodeURIComponent(htmlRef)}`);
    
    if (!response.ok) {
      throw new Error("Unable to retrieve article body text");
    }

    const data = await response.json();
    state.activeArticleData = data;
    
    // Call modular rendering function
    renderArticleContent();

    readerLoader.style.display = 'none';
    readerContent.style.display = 'block';
  } catch (error) {
    captureException(error);
    readerLoader.style.display = 'none';
    const errorDiv = document.createElement('div');
    errorDiv.className = 'empty-state';
    errorDiv.style.color = '#c5221f';
    errorDiv.innerHTML = `<h3 class="empty-state-title">Loading Failed</h3>
                          <p class="empty-state-desc">The server is unable to fetch the article text. Please try again later.</p>`;
    readerBody.innerHTML = '';
    readerBody.appendChild(errorDiv);
    readerContent.style.display = 'block';
  } finally {
    state.isArticleLoading = false;
  }
}

function renderArticleContent() {
  if (!state.activeArticleData) return;
  const data = state.activeArticleData;
  const htmlRef = state.activeArticleRef;

  const textVideFn = typeof window.textVide === 'function'
    ? window.textVide
    : (window.textVide && typeof window.textVide.textVide === 'function' ? window.textVide.textVide : null);

  // Safely insert content using textContent to prevent XSS
  readerCategory.textContent = state.city.replace('th_', '').toUpperCase();
  readerHeadline.textContent = data.headline || "Untitled Article";
  readerByline.textContent = data.author ? `By ${data.author}` : "";
  readerDateline.textContent = data.dateline || "";

  // Save the scroll position of the reader pane
  const savedScrollTop = readerPane.scrollTop;

  // Clear body and render paragraphs
  readerBody.innerHTML = '';

  // Find article metadata in local state to check for associated images
  let articleMeta = null;
  for (const page of (state.rawPages || [])) {
    articleMeta = page.articles.find(art => art.html_ref === htmlRef);
    if (articleMeta) break;
  }

  // Render associated images as cover illustrations
  if (articleMeta && articleMeta.images && articleMeta.images.length > 0) {
    articleMeta.images.forEach(imgRef => {
      const img = document.createElement('img');
      img.src = `https://epaper.thehindu.com/ccidist-ws/th/${state.city}/issues/${state.issueId}/OPS/${imgRef}`;
      img.alt = "Article Illustration";
      img.style.width = '100%';
      img.style.maxHeight = '450px';
      img.style.objectFit = 'contain';
      img.style.margin = '0 0 24px 0';
      img.style.borderRadius = '4px';
      img.style.border = '1px solid var(--border-color)';
      readerBody.appendChild(img);
    });
  }
  
  // Highlights if present
  if (data.highlights && data.highlights.length > 0) {
    data.highlights.forEach(quote => {
      const div = document.createElement('div');
      div.className = 'highlight-box';
      
      if (state.bionicReading && textVideFn) {
        const escaped = escapeHTML(quote);
        div.innerHTML = textVideFn(escaped, {
          ignoreHtmlTag: true,
          ignoreHtmlEntity: true,
          fixationPoint: state.fixationPoint
        });
      } else {
        div.textContent = quote;
      }
      
      readerBody.appendChild(div);
    });
  }

  // Body Paragraphs
  if (data.body && data.body.length > 0) {
    data.body.forEach(paraText => {
      const p = document.createElement('p');
      
      if (state.bionicReading && textVideFn) {
        const escaped = escapeHTML(paraText);
        p.innerHTML = textVideFn(escaped, {
          ignoreHtmlTag: true,
          ignoreHtmlEntity: true,
          fixationPoint: state.fixationPoint
        });
      } else {
        p.textContent = paraText;
      }
      
      readerBody.appendChild(p);
    });
  } else {
    const p = document.createElement('p');
    p.style.fontStyle = 'italic';
    p.textContent = "No body paragraphs found for this item.";
    readerBody.appendChild(p);
  }

  // Restore the scroll position
  readerPane.scrollTop = savedScrollTop;
}

function closeArticleReader(pushHistory = true) {
  state.activeArticleRef = null;
  state.activeArticleData = null; // Clear cached content to free memory
  
  if (pushHistory) {
    syncUrlHistory();
  }

  // Hide overlay
  readerPane.style.display = 'none';
  readerContent.style.display = 'none';
  readerProgressBar.style.width = '0%';

  // Remove listeners
  window.removeEventListener('keydown', handleEscapeKey);
  readerPane.removeEventListener('scroll', handleReaderProgress);

  // Restore scroll coordinates (removes iOS lock)
  document.body.classList.remove('reader-open');
  document.body.style.top = '';
  window.scrollTo(0, state.savedScrollY);

  // Restore keyboard focus to triggering element
  if (state.focusTrigger) {
    state.focusTrigger.focus();
    state.focusTrigger = null;
  }
}

// Escape key press handler
function handleEscapeKey(e) {
  if (e.key === 'Escape') {
    closeArticleReader();
  }
}

// Progress bar width updater
function handleReaderProgress() {
  const progress = (readerPane.scrollTop) / (readerPane.scrollHeight - readerPane.clientHeight) * 100;
  readerProgressBar.style.width = `${progress}%`;
}
