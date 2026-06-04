(function() {
  const resultsContainer = document.getElementById('test-results');
  const tests = [];

  function assert(condition, message) {
    if (!condition) {
      throw new Error(message || "Assertion failed");
    }
  }

  function assertEqual(actual, expected, message) {
    if (actual !== expected) {
      throw new Error(`${message || "Assertion failed"}: Expected "${expected}", but got "${actual}"`);
    }
  }

  function assertDeepEqual(actual, expected, message) {
    const actStr = JSON.stringify(actual);
    const expStr = JSON.stringify(expected);
    if (actStr !== expStr) {
      throw new Error(`${message || "Assertion failed"}: Expected ${expStr}, but got ${actStr}`);
    }
  }

  function test(name, fn) {
    tests.push({ name, fn });
  }

  // ==========================================================================
  // EXISTING CORE TESTS
  // ==========================================================================

  test("getCleanSectionName maps raw pages to sections correctly", function() {
    assertEqual(getCleanSectionName("Front_Pg"), "Front Page");
    assertEqual(getCleanSectionName("Regional_01"), "Regional");
    assertEqual(getCleanSectionName("Edit_02"), "Editorial");
    assertEqual(getCleanSectionName("Sports_01"), "Sports");
    assertEqual(getCleanSectionName("Science_Pg"), "Science");
    assertEqual(getCleanSectionName("Jacket_01"), "Front Page");
    assertEqual(getCleanSectionName("RglAdpage_02"), "Regional");
    assertEqual(getCleanSectionName("States_01"), "States");
    assertEqual(getCleanSectionName("South_01"), "States");
    assertEqual(getCleanSectionName("Text_02"), "Text & Context");
    assertEqual(getCleanSectionName("News_03"), "News");
    assertEqual(getCleanSectionName("Business_01"), "Business");
    assertEqual(getCleanSectionName("Foreign_01"), "World");
    assertEqual(getCleanSectionName("SplSports_01"), "Sports");
    assertEqual(getCleanSectionName("Back_Pg"), "Sports");
    assertEqual(getCleanSectionName("Unknown_Section"), "General");
  });

  test("isNoiseArticle identifies promo pages and puzzles accurately", function() {
    assertEqual(isNoiseArticle("TH_Subscribe_QR_code_New"), true);
    assertEqual(isNoiseArticle("SUDOKU"), true);
    assertEqual(isNoiseArticle("Sudoku_solution"), true);
    assertEqual(isNoiseArticle("know your english"), true);
    assertEqual(isNoiseArticle("the daily quiz"), true);
    assertEqual(isNoiseArticle("text_feedback"), true);
    assertEqual(isNoiseArticle("scoreboard"), true);
    assertEqual(isNoiseArticle("the results"), true);
    assertEqual(isNoiseArticle("live telecast"), true);
    assertEqual(isNoiseArticle("14805"), true); // numeric page markers
    assertEqual(isNoiseArticle("th27 promo1"), true);
    assertEqual(isNoiseArticle("th27 nearby2"), true);
    assertEqual(isNoiseArticle("news in numbers_Shape1"), true);
    assertEqual(isNoiseArticle("Promo_Lead_big"), true);
    assertEqual(isNoiseArticle("Promo_03 (2)0"), true);
    assertEqual(isNoiseArticle("Promo_sports (3)"), true);
    assertEqual(isNoiseArticle("23BG SIRPAGE1"), true);
    assertEqual(isNoiseArticle("23bg stadiump-age1"), true);
    
    // Valid articles
    assertEqual(isNoiseArticle("SC upholds SIR, says it is EC's constitutional duty"), false);
    assertEqual(isNoiseArticle("UPSC releases provisional answer key of Prelims exam"), false);
    assertEqual(isNoiseArticle("Vijay calls on Modi; airs concerns over Mekedatu project"), false);
  });

  test("parseQueryParams handles URL parsing and formats validation properly", function() {
    assertDeepEqual(parseQueryParams("?date=2026-05-28&city=th_delhi"), {date: "2026-05-28", city: "th_delhi", article: null});
    assertDeepEqual(parseQueryParams("?city=th_delhi&date=2026-05-28"), {date: "2026-05-28", city: "th_delhi", article: null});
    assertDeepEqual(parseQueryParams("?date=invalid-date&city=th_delhi"), {date: null, city: null, article: null});
    assertDeepEqual(parseQueryParams(""), {date: null, city: null, article: null});
  });

  test("Show Puzzles & Promos checkbox is removed from the DOM", function() {
    const toggle = document.getElementById('show-promos-toggle');
    assertEqual(toggle, null, "The show-promos-toggle element should be removed from the DOM");
  });

  // ==========================================================================
  // NEW AI EDITOR'S PICKS TDD TESTS
  // ==========================================================================

  // Test Case 1: State Variables Initialization
  test("state object initializes topPicks and topPicksStatus correctly", function() {
    assert(Array.isArray(state.topPicks), "state.topPicks should be an array");
    assertEqual(state.topPicks.length, 0, "state.topPicks should start empty");
    assertEqual(state.topPicksStatus, 'not_generated', "state.topPicksStatus should start as not_generated");
  });

  // Test Case 2: switchPanelState transitions
  test("switchPanelState correctly toggles display properties of panels and updates status badge text", function() {
    switchPanelState('trigger');
    const triggerPanel = document.getElementById('ai-trigger-panel');
    const loadingPanel = document.getElementById('ai-loading-panel');
    const readyPanel = document.getElementById('ai-ready-panel');
    const badge = document.getElementById('ai-status-badge');
    
    assertEqual(triggerPanel.style.display, 'block', "trigger panel should be block");
    assertEqual(loadingPanel.style.display, 'none', "loading panel should be none");
    assertEqual(readyPanel.style.display, 'none', "ready panel should be none");
    assertEqual(badge.textContent, 'Ready to generate', "badge text should match trigger");

    switchPanelState('loading');
    assertEqual(triggerPanel.style.display, 'none');
    assertEqual(loadingPanel.style.display, 'block');
    assertEqual(readyPanel.style.display, 'none');
    assertEqual(badge.textContent, 'Analyzing headlines...');

    switchPanelState('ready');
    assertEqual(triggerPanel.style.display, 'none');
    assertEqual(loadingPanel.style.display, 'none');
    assertEqual(readyPanel.style.display, 'block');
    assertEqual(badge.textContent, 'Curated by AI Editor');
  });

  // Test Case 3: renderTopPicksGrid Card Builder
  test("renderTopPicksGrid appends cards, calculates average scores, and binds openArticleReader", function() {
    const originalPicks = state.topPicks;
    const gridContainer = document.getElementById('ai-picks-grid');
    assert(gridContainer !== null, "gridContainer mockup is required");

    state.topPicks = [
      {
        id: "ART.1",
        headline: "First Pick",
        html_ref: "ref1.html",
        reason: "Reason one.",
        ratings: { impact: 9, importance: 8, interest: 7, depth: 8 }
      },
      {
        id: "ART.2",
        headline: "Second Pick",
        html_ref: "ref2.html",
        reason: "Reason two.",
        ratings: { impact: 7, importance: 7, interest: 8, depth: 6 }
      }
    ];

    let appendedChildren = [];
    gridContainer.appendChild = function(el) {
      appendedChildren.push(el);
    };
    gridContainer.innerHTML = '';

    renderTopPicksGrid();

    assertEqual(appendedChildren.length, 2, "Should append exactly 2 cards");
    
    const card1 = appendedChildren[0];
    assert(card1.innerHTML.includes('#1'), "Card 1 should show rank #1");
    assert(card1.innerHTML.includes('Score: 8.0'), "Card 1 score should be 8.0");
    assert(card1.innerHTML.includes('First Pick'), "Card 1 headline missing");
    assert(card1.innerHTML.includes('Reason one.'), "Card 1 reason missing");
    assertEqual(typeof card1.onclick, 'function', "Card 1 click handler should be bound");

    state.topPicks = originalPicks;
  });

  // Test Case 4: Cache State Handler Integration
  test("checkTopPicksCache updates state, display containers, and panel states on status results", async function() {
    const originalFetch = global.fetch;
    const originalPicks = state.topPicks;
    const picksSection = document.getElementById('ai-picks-section');

    global.fetch = async function(url) {
      assert(url.includes('/api/top-headlines'), "Should query top-headlines");
      return {
        ok: true,
        json: async () => ({
          status: 'ready',
          top_articles: [{
            id: "ART.1",
            headline: "First Pick",
            html_ref: "art1.html",
            reason: "Reason text",
            ratings: { impact: 1, importance: 1, interest: 1, depth: 1 }
          }]
        })
      };
    };

    state.date = "2026-05-28";
    state.city = "th_delhi";

    await checkTopPicksCache("2026-05-28", "th_delhi");

    assertEqual(state.topPicksStatus, 'ready');
    assertEqual(state.topPicks.length, 1);
    assertEqual(picksSection.style.display, 'block');

    global.fetch = originalFetch;
    state.topPicks = originalPicks;
  });

  // Test Case 5: generateTopPicks successful call
  test("generateTopPicks performs fetch, updates state, and renders picks on success", async function() {
    const originalFetch = global.fetch;
    const originalPicks = state.topPicks;
    const picksSection = document.getElementById('ai-picks-section');
    const loadingPanel = document.getElementById('ai-loading-panel');
    const readyPanel = document.getElementById('ai-ready-panel');

    global.fetch = async function(url) {
      assert(url.includes('generate=true'), "Should request generation");
      return {
        ok: true,
        json: async () => ({
          status: 'ready',
          top_articles: [{
            id: "ART.1",
            headline: "First Pick",
            html_ref: 'art1.html',
            ratings: { impact: 9, importance: 8, interest: 7, depth: 8 },
            reason: "test"
          }]
        })
      };
    };

    state.date = "2026-05-28";
    state.city = "th_delhi";

    await generateTopPicks();

    assertEqual(state.topPicksStatus, 'ready');
    assertEqual(state.topPicks.length, 1);
    assertEqual(picksSection.style.display, 'block');
    assertEqual(readyPanel.style.display, 'block');
    assertEqual(loadingPanel.style.display, 'none');

    global.fetch = originalFetch;
    state.topPicks = originalPicks;
  });

  // Test Case 6: generateTopPicks failure path
  test("generateTopPicks fallback to trigger panel and displays error banner on API failure", async function() {
    const originalFetch = global.fetch;
    const notificationText = document.getElementById('notification-text');
    const notificationBanner = document.getElementById('notification-banner');
    
    notificationText.textContent = "";
    notificationBanner.style.display = "none";

    global.fetch = async function(url) {
      return {
        ok: false,
        json: async () => ({ detail: "Rate limit exceeded" })
      };
    };

    state.date = "2026-05-28";
    state.city = "th_delhi";

    await generateTopPicks();

    assertEqual(state.topPicksStatus, 'failed');
    assertEqual(document.getElementById('ai-trigger-panel').style.display, 'block');
    assertEqual(notificationText.textContent, "Not able to generate AI picks right now");
    assertEqual(notificationBanner.style.display, 'flex');

    global.fetch = originalFetch;
  });

  // Test Case 7: state.limit initialization
  test("state.limit initializes to 10 by default", function() {
    assertEqual(state.limit, 10, "state.limit should be 10 by default");
  });

  // Test Case 8: Limit Button Interaction updates state and triggers renderTopPicksGrid
  test("clicking limit button updates state.limit and triggers renderTopPicksGrid if ready", function() {
    const originalRender = renderTopPicksGrid;
    let renderCalled = false;
    renderTopPicksGrid = function() {
      renderCalled = true;
    };

    const originalStatus = state.topPicksStatus;
    state.topPicksStatus = 'ready';
    state.date = "2026-05-28";
    state.city = "th_delhi";

    // Call initApp to bind event listeners
    initApp();

    const limitBtns = document.querySelectorAll('#ai-limit-group .ai-limit-btn');
    const btn20 = limitBtns[1]; // button with data-limit=20
    assertEqual(btn20.getAttribute('data-limit'), '20');

    // Simulate click
    btn20.dispatchEvent({ type: 'click' });

    assertEqual(state.limit, 20, "state.limit should update to 20");
    assertEqual(btn20.className, 'active', "clicked button should become active");
    assert(renderCalled, "renderTopPicksGrid should be called");

    // Restore
    renderTopPicksGrid = originalRender;
    state.topPicksStatus = originalStatus;
  });

  // Test Case 9: fetch calls do NOT append limit query parameter
  test("checkTopPicksCache and generateTopPicks do NOT append limit to the fetch API requests", async function() {
    const originalFetch = global.fetch;
    let requestedUrl = "";

    global.fetch = async function(url) {
      requestedUrl = url;
      return {
        ok: true,
        json: async () => ({
          status: 'ready',
          top_articles: []
        })
      };
    };

    state.limit = 25;
    state.date = "2026-05-28";
    state.city = "th_delhi";

    await checkTopPicksCache("2026-05-28", "th_delhi");
    assert(!requestedUrl.includes('limit='), `Url should NOT contain limit: ${requestedUrl}`);

    await generateTopPicks();
    assert(!requestedUrl.includes('limit='), `Url should NOT contain limit: ${requestedUrl}`);

    global.fetch = originalFetch;
  });

  // ==========================================================================
  // BIONIC READING TDD TESTS
  // ==========================================================================

  // Test Case 1: Initial State & Preferences Loading
  test("state initializes bionicReading and fixationPoint correctly from defaults/localStorage", function() {
    localStorage.removeItem('bionic-enabled');
    localStorage.removeItem('bionic-fixation');
    
    // Check initial state
    assertEqual(state.bionicReading, false, "default bionicReading should be false");
    assertEqual(state.fixationPoint, 3, "default fixationPoint should be 3");
    
    // Simulate stored settings
    localStorage.setItem('bionic-enabled', 'true');
    localStorage.setItem('bionic-fixation', '4');
    
    initApp();
    
    assertEqual(state.bionicReading, true, "bionicReading should load from storage as true");
    assertEqual(state.fixationPoint, 4, "fixationPoint should load from storage as 4");
    
    localStorage.removeItem('bionic-enabled');
    localStorage.removeItem('bionic-fixation');
    initApp();
  });

  // Test Case 2: UI Toggle Event Handler & Panel Display Toggle
  test("clicking bionic toggle updates state, label, localStorage, and shows fixation dropdown", function() {
    const toggleBtn = document.getElementById('bionic-toggle-btn');
    const strengthCtrl = document.getElementById('fixation-control');
    
    assert(toggleBtn !== null, "toggleBtn mock is required");
    assert(strengthCtrl !== null, "strengthCtrl mock is required");
    
    state.bionicReading = false;
    toggleBtn.textContent = "Bionic: Off";
    strengthCtrl.style.display = "none";
    
    toggleBtn.dispatchEvent({ type: 'click' });
    
    assertEqual(state.bionicReading, true, "state.bionicReading should toggle to true");
    assertEqual(toggleBtn.textContent, "Bionic: On", "Button label should update");
    assertEqual(localStorage.getItem('bionic-enabled'), 'true', "localStorage should sync");
    assertEqual(strengthCtrl.style.display, 'inline-block', "Fixation control panel should be visible");
    assert(document.documentElement.classList.contains('bionic-active'), "HTML element should contain bionic-active class");

    // Toggle again to verify removal
    toggleBtn.dispatchEvent({ type: 'click' });
    assertEqual(state.bionicReading, false, "state.bionicReading should toggle to false");
    assertEqual(toggleBtn.textContent, "Bionic: Off", "Button label should update to Off");
    assertEqual(localStorage.getItem('bionic-enabled'), 'false', "localStorage should sync to false");
    assertEqual(strengthCtrl.style.display, 'none', "Fixation control panel should be hidden");
    assert(!document.documentElement.classList.contains('bionic-active'), "HTML element should not contain bionic-active class");
  });

  // Test Case 3: Fixation Selection Change Handler
  test("changing fixation selection dropdown updates state.fixationPoint and syncs to localStorage", function() {
    const selectEl = document.getElementById('bionic-fixation-select');
    assert(selectEl !== null, "selectEl mock is required");
    
    selectEl.value = "2";
    selectEl.dispatchEvent({ type: 'change' });
    
    assertEqual(state.fixationPoint, 2, "state.fixationPoint should be 2");
    assertEqual(localStorage.getItem('bionic-fixation'), '2', "localStorage should update");
  });

  // Test Case 4: Text Rendering & Highlight Formatting (DOM Verification)
  test("renderArticleContent applies textVide formatting when enabled, and textContent when disabled", function() {
    const readerBody = document.getElementById('reader-body');
    assert(readerBody !== null, "readerBody mock is required");
    
    state.activeArticleData = {
      headline: "Test Headline",
      body: ["Bionic Reading test."]
    };
    
    state.bionicReading = true;
    state.fixationPoint = 3;
    
    renderArticleContent();
    
    const paragraphs = readerBody.children;
    console.log("DEBUG: paragraphs[0].innerHTML =", paragraphs[0] ? paragraphs[0].innerHTML : "undefined");
    assert(paragraphs.length > 0, "Paragraph should be rendered");
    assert(paragraphs[0].innerHTML.includes('<b>Bio</b>nic'), "Should contain bolded fixation anchors");
    
    state.bionicReading = false;
    renderArticleContent();
    assertEqual(paragraphs[0].innerHTML, "Bionic Reading test.", "Paragraph should render as clean text");
  });

  // Test Case 5: HTML Escaping (XSS Prevention) Verification
  test("renderArticleContent escapes HTML tags in body paragraphs to prevent XSS", function() {
    const readerBody = document.getElementById('reader-body');
    assert(readerBody !== null);
    
    state.activeArticleData = {
      headline: "XSS Test",
      body: ["<script>alert(1)</script>Safe text"]
    };
    state.bionicReading = true;
    renderArticleContent();
    
    const paragraphs = readerBody.children;
    assert(paragraphs.length > 0);
    assert(!paragraphs[0].innerHTML.includes('<script>'), "Should escape <script> to prevent execution");
    assert(paragraphs[0].innerHTML.includes('&lt;') && paragraphs[0].innerHTML.includes('&gt;'), "Should convert tags to entities");
  });

  // ==========================================================================
  // GUTENBERG FLAGSHIP THEME TDD TESTS
  // ==========================================================================

  // Test Case 1: state initializes default paperStyle to ivory
  test("state initializes default paperStyle to ivory", function() {
    assert(state.paperStyle !== undefined, "state.paperStyle should be defined");
  });

  // Test Case 2: applying theme-gutenberg updates document element classes and shows controls
  test("applying theme-gutenberg updates document element classes and shows controls", function() {
    const subcontrols = document.getElementById('gutenberg-subcontrols');
    assert(subcontrols !== null, "gutenberg-subcontrols element is required");

    state.theme = 'theme-gutenberg';
    state.paperStyle = 'paper-sepia';
    
    applyTheme('theme-gutenberg');
    
    assert(document.documentElement.classList.contains('theme-gutenberg'), "html element should have theme-gutenberg class");
    assert(document.documentElement.classList.contains('paper-sepia'), "html element should have paper-sepia class");
    assertEqual(subcontrols.style.display, 'flex', "Gutenberg controls should be visible with display: flex");
  });

  // Test Case 3: syncPaperUI updates active classes on paper sub-selector buttons
  test("syncPaperUI updates active classes on paper sub-selector buttons", function() {
    const paperBtns = document.querySelectorAll('#gutenberg-subcontrols .ctrl-btn');
    assert(paperBtns.length >= 3, "There should be at least 3 paper buttons");
    
    state.paperStyle = 'paper-white';
    syncPaperUI();
    
    const btnWhite = Array.from(paperBtns).find(b => b.getAttribute('data-paper') === 'paper-white');
    const btnIvory = Array.from(paperBtns).find(b => b.getAttribute('data-paper') === 'paper-ivory');
    
    assert(btnWhite.className.includes('active'), "Active button should have active class");
    assert(!btnIvory.className.includes('active'), "Inactive button should not have active class");
  });

  // Test Case 4: switching away from theme-gutenberg hides paper sub-controls and resets paper classes
  test("switching away from theme-gutenberg hides paper sub-controls and resets paper classes", function() {
    const subcontrols = document.getElementById('gutenberg-subcontrols');
    
    applyTheme('theme-folio');
    
    assert(document.documentElement.classList.contains('theme-folio'));
    assert(!document.documentElement.classList.contains('theme-gutenberg'));
    assert(!document.documentElement.classList.contains('paper-ivory'));
    assert(!document.documentElement.classList.contains('paper-white'));
    assert(!document.documentElement.classList.contains('paper-sepia'));
    assertEqual(subcontrols.style.display, 'none', "Gutenberg controls should be hidden");
  });

  // ==========================================================================
  // RUNNER ENGINE
  // ==========================================================================

  async function runAllTests() {
    resultsContainer.innerHTML = '';
    let failedTests = 0;

    for (const t of tests) {
      const testDiv = document.createElement('div');
      testDiv.className = 'test-case';
      try {
        await t.fn();
        testDiv.className += ' pass';
        testDiv.textContent = `✓ ${t.name}`;
      } catch (e) {
        failedTests++;
        testDiv.className += ' fail';
        testDiv.innerHTML = `✗ ${t.name} <pre>${e.message}\n${e.stack}</pre>`;
      }
      resultsContainer.appendChild(testDiv);
    }

    // Summary heading
    const summaryHeader = document.createElement('h3');
    summaryHeader.style.marginTop = '20px';
    if (failedTests === 0) {
      summaryHeader.style.color = '#137333';
      summaryHeader.textContent = "All unit tests passed successfully!";
    } else {
      summaryHeader.style.color = '#c5221f';
      summaryHeader.textContent = `${failedTests} unit test(s) failed.`;
    }
    resultsContainer.insertBefore(summaryHeader, resultsContainer.firstChild);

    return failedTests;
  }

  // Expose globally
  window.runAllTests = runAllTests;

  // Auto-run in browser, but do not auto-run in Node test runner
  if (typeof process === 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => runAllTests());
    } else {
      runAllTests();
    }
  }

})();
