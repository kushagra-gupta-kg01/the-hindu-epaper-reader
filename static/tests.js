(function() {
  const resultsContainer = document.getElementById('test-results');
  resultsContainer.innerHTML = '';
  let failedTests = 0;

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
    const testDiv = document.createElement('div');
    testDiv.className = 'test-case';
    
    try {
      fn();
      testDiv.className += ' pass';
      testDiv.textContent = `✓ ${name}`;
    } catch (e) {
      failedTests++;
      testDiv.className += ' fail';
      testDiv.innerHTML = `✗ ${name} <pre>${e.message}\n${e.stack}</pre>`;
    }
    
    resultsContainer.appendChild(testDiv);
  }

  // Define Tests

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

})();
