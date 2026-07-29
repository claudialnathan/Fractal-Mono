(() => {
  "use strict";

  const data = window.CLN_MONO_DATA;

  if (!data) {
    document.body.dataset.specimenError = "missing-data";
    return;
  }

  const root = document.documentElement;
  const weightAxis = data.axes.wght;
  const opticalAxis = data.axes.opsz;
  const formatNumber = new Intl.NumberFormat("en");
  const normalise = (value) =>
    String(value ?? "")
      .normalize("NFKD")
      .toLocaleLowerCase("en");

  const setText = (selector, value) => {
    document.querySelectorAll(selector).forEach((element) => {
      element.textContent = value;
    });
  };

  const factValues = {
    version: data.version,
    axis: `${weightAxis.tag} ${weightAxis.min}–${weightAxis.max} · ${opticalAxis.tag} ${opticalAxis.min}–${opticalAxis.max}`,
    instances: formatNumber.format(data.instances.length),
    glyphs: formatNumber.format(data.glyphCount),
    characters: formatNumber.format(data.encodedCount),
    features: formatNumber.format(data.featureCount),
    advance: `${data.metrics.advanceWidth} / ${data.metrics.unitsPerEm} UPM`,
    languages: formatNumber.format(data.languageCount),
  };

  Object.entries(factValues).forEach(([name, value]) => {
    setText(`[data-fact="${name}"]`, value);
  });
  setText("[data-footer-version]", data.version);
  setText("[data-file-count]", `${formatNumber.format(data.files.length)} files`);

  const themeToggle = document.querySelector(".theme-toggle");
  const themeStorageKey = "cln-mono-specimen-theme";

  const preferredTheme = () => {
    try {
      const saved = window.localStorage.getItem(themeStorageKey);
      if (saved === "light" || saved === "dark") {
        return saved;
      }
    } catch {
      // The specimen still works when local storage is disabled or opened locally.
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const applyTheme = (theme, persist = false) => {
    root.dataset.theme = theme;
    themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
    themeToggle.textContent = theme === "dark" ? "Light" : "Dark";
    themeToggle.setAttribute(
      "aria-label",
      `Use ${theme === "dark" ? "light" : "dark"} appearance`,
    );
    if (persist) {
      try {
        window.localStorage.setItem(themeStorageKey, theme);
      } catch {
        // A saved preference is optional.
      }
    }
  };

  applyTheme(preferredTheme());
  themeToggle.addEventListener("click", () => {
    applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
  });

  const testerDefaults = {
    weight: weightAxis.default,
    optical: opticalAxis.default,
    size: 72,
    leading: 1.05,
    tracking: 0,
    align: "left",
    ligatures: false,
  };
  const testerState = { ...testerDefaults };
  const testerWeight = document.querySelector("#tester-weight");
  const testerOptical = document.querySelector("#tester-optical");
  const testerSize = document.querySelector("#tester-size");
  const testerLeading = document.querySelector("#tester-leading");
  const testerTracking = document.querySelector("#tester-tracking");
  const weightOutput = document.querySelector("#tester-weight-output");
  const opticalOutput = document.querySelector("#tester-optical-output");
  const alignButtons = [...document.querySelectorAll("[data-align]")];
  const ligatureToggles = [...document.querySelectorAll(".ligature-toggle")];
  const instanceButtonWrap = document.querySelector("[data-instance-buttons]");

  const clamp = (value, minimum, maximum) =>
    Math.min(maximum, Math.max(minimum, value));

  const updateTester = () => {
    root.style.setProperty("--tester-weight", testerState.weight);
    root.style.setProperty("--tester-optical", testerState.optical);
    root.style.setProperty("--tester-size", `${testerState.size}px`);
    root.style.setProperty("--tester-leading", testerState.leading);
    root.style.setProperty("--tester-tracking", `${testerState.tracking}em`);
    root.style.setProperty("--tester-align", testerState.align);
    root.classList.toggle("ligatures-enabled", testerState.ligatures);

    testerWeight.value = testerState.weight;
    testerWeight.setAttribute(
      "aria-valuetext",
      `${testerState.weight} weight`,
    );
    testerOptical.value = testerState.optical;
    testerOptical.setAttribute(
      "aria-valuetext",
      `${testerState.optical} optical size`,
    );
    testerSize.value = testerState.size;
    testerLeading.value = testerState.leading;
    testerTracking.value = testerState.tracking;
    weightOutput.value = testerState.weight;
    weightOutput.textContent = testerState.weight;
    opticalOutput.value = testerState.optical;
    opticalOutput.textContent = testerState.optical;

    setText('[data-readout="weight"]', testerState.weight);
    setText('[data-readout="optical"]', testerState.optical);
    setText('[data-readout="size"]', testerState.size);
    setText('[data-readout="leading"]', testerState.leading);
    setText('[data-readout="tracking"]', testerState.tracking);

    instanceButtonWrap.querySelectorAll("button").forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        String(Number(button.dataset.weight) === Number(testerState.weight)),
      );
    });
    alignButtons.forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.align === testerState.align),
      );
    });
    ligatureToggles.forEach((input) => {
      input.checked = testerState.ligatures;
    });
  };

  data.instances.forEach((instance) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.weight = instance.value;
    button.textContent = instance.value;
    button.title = instance.name;
    button.setAttribute(
      "aria-label",
      `${instance.name}, weight ${instance.value}`,
    );
    button.addEventListener("click", () => {
      testerState.weight = instance.value;
      updateTester();
    });
    instanceButtonWrap.append(button);
  });

  testerWeight.addEventListener("input", () => {
    testerState.weight = Number(testerWeight.value);
    updateTester();
  });
  testerOptical.addEventListener("input", () => {
    testerState.optical = Number(testerOptical.value);
    updateTester();
  });

  [
    [testerSize, "size", 12, 192],
    [testerLeading, "leading", 0.8, 2],
    [testerTracking, "tracking", -0.08, 0.2],
  ].forEach(([input, key, minimum, maximum]) => {
    input.addEventListener("input", () => {
      const value = Number(input.value);
      if (Number.isFinite(value)) {
        testerState[key] = clamp(value, minimum, maximum);
        updateTester();
      }
    });
  });

  alignButtons.forEach((button) => {
    button.addEventListener("click", () => {
      testerState.align = button.dataset.align;
      updateTester();
    });
  });

  ligatureToggles.forEach((toggle) => {
    toggle.addEventListener("change", () => {
      testerState.ligatures = toggle.checked;
      updateTester();
    });
  });

  document.querySelector("#tester-reset").addEventListener("click", () => {
    Object.assign(testerState, testerDefaults);
    updateTester();
  });
  updateTester();

  const weightWaterfall = document.querySelector("[data-weight-waterfall]");
  data.instances.forEach((instance) => {
    const row = document.createElement("article");
    row.className = "weight-row";

    const meta = document.createElement("div");
    meta.className = "weight-meta";
    const name = document.createElement("strong");
    name.textContent = instance.name;
    const value = document.createElement("span");
    value.textContent = instance.value;
    meta.append(name, value);

    const sample = document.createElement("p");
    sample.textContent = "Fixed cells. Flexible voice.";
    sample.contentEditable = "true";
    sample.spellcheck = false;
    sample.style.fontWeight = instance.value;
    sample.setAttribute(
      "aria-label",
      `Editable ${instance.name} weight specimen`,
    );
    row.append(meta, sample);
    weightWaterfall.append(row);
  });

  const featureGrid = document.querySelector("#feature-grid");
  const featurePreview = document.querySelector("#feature-preview");
  const activeFeatureCount = document.querySelector("#active-feature-count");
  const featureInputs = new Map();

  const featureSetting = (tag, enabled) => `"${tag}" ${enabled ? 1 : 0}`;

  const updateFeaturePreview = () => {
    const selected = [];
    let optionalCount = 0;
    featureInputs.forEach((input, tag) => {
      if (input.checked) {
        selected.push(featureSetting(tag, true));
        if (input.dataset.status === "optional") {
          optionalCount += 1;
        }
      }
    });
    featurePreview.style.fontFeatureSettings = selected.length
      ? selected.join(", ")
      : "normal";
    activeFeatureCount.value = optionalCount;
    activeFeatureCount.textContent = `${optionalCount} optional ${
      optionalCount === 1 ? "feature" : "features"
    } active`;
  };

  data.features.forEach((feature) => {
    const card = document.createElement("article");
    card.className = "feature-card";
    card.dataset.feature = feature.tag;

    const header = document.createElement("div");
    header.className = "feature-card-header";
    const tag = document.createElement("code");
    tag.className = "feature-tag";
    tag.textContent = feature.tag;
    const status = document.createElement("span");
    status.className = "feature-status";
    status.textContent = feature.status;
    header.append(tag, status);

    const heading = document.createElement("h3");
    heading.textContent = feature.name;
    const description = document.createElement("p");
    description.className = "feature-card-description";
    description.textContent = `${feature.description} ${formatNumber.format(
      feature.lookups,
    )} ${feature.lookups === 1 ? "lookup" : "lookups"}.`;

    const comparison = document.createElement("div");
    comparison.className = "feature-comparison";
    [
      ["Off", false],
      ["On", true],
    ].forEach(([label, enabled]) => {
      const panel = document.createElement("div");
      const caption = document.createElement("span");
      caption.textContent = label;
      const sample = document.createElement("p");
      sample.textContent = feature.sample;
      sample.style.fontFeatureSettings = featureSetting(feature.tag, enabled);
      panel.append(caption, sample);
      comparison.append(panel);
    });

    let control;
    if (feature.status === "automatic") {
      control = document.createElement("p");
      control.className = "feature-toggle feature-automatic";
      control.textContent = "Applied automatically by the shaping engine";
    } else {
      control = document.createElement("label");
      control.className = "feature-toggle";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = feature.status === "default";
      input.dataset.status = feature.status;
      input.setAttribute("aria-label", `Enable ${feature.tag}: ${feature.name}`);
      input.addEventListener("change", updateFeaturePreview);
      const labelText = document.createElement("span");
      labelText.textContent =
        feature.status === "default"
          ? "Enabled by default"
          : "Add to combined preview";
      control.append(input, labelText);
      featureInputs.set(feature.tag, input);
    }

    card.append(header, heading, description, comparison, control);
    featureGrid.append(card);
  });

  document.querySelector("#clear-features").addEventListener("click", () => {
    featureInputs.forEach((input) => {
      input.checked = input.dataset.status === "default";
    });
    updateFeaturePreview();
  });
  updateFeaturePreview();

  const coverageSummary = document.querySelector("[data-coverage-summary]");
  const leadingBlocks = Object.entries(data.blockSummary)
    .slice(0, 3)
    .map(([block]) => block)
    .join(", ");
  [
    [data.glyphCount, "Total glyphs"],
    [data.encodedCount, "Encoded characters"],
    [data.unencodedCount, "Alternates and drawings"],
    [Object.keys(data.blockSummary).length, `${leadingBlocks} lead ${Object.keys(data.blockSummary).length} Unicode blocks`],
  ].forEach(([value, label]) => {
    const card = document.createElement("article");
    const strong = document.createElement("strong");
    strong.textContent = formatNumber.format(value);
    const span = document.createElement("span");
    span.textContent = label;
    card.append(strong, span);
    coverageSummary.append(card);
  });

  const characterSearch = document.querySelector("#character-search");
  const scriptFilter = document.querySelector("#script-filter");
  const characterCount = document.querySelector("#character-count");
  const glyphGrid = document.querySelector("#glyph-grid");
  const glyphInspector = document.querySelector("#glyph-inspector");
  const characterEmpty = document.querySelector("#character-empty");
  const characterButtons = [];
  let selectedCharacterButton;

  Object.entries(data.scriptSummary)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .forEach(([script, count]) => {
      const option = document.createElement("option");
      option.value = script;
      option.textContent = `${script} (${formatNumber.format(count)})`;
      scriptFilter.append(option);
    });

  const showCharacter = (character, button) => {
    if (selectedCharacterButton) {
      selectedCharacterButton.setAttribute("aria-pressed", "false");
      selectedCharacterButton.tabIndex = -1;
    }
    selectedCharacterButton = button;
    selectedCharacterButton.setAttribute("aria-pressed", "true");
    selectedCharacterButton.tabIndex = 0;

    glyphInspector.querySelector(".inspector-glyph").textContent = character.display;
    const values = glyphInspector.querySelectorAll("dd");
    values[0].textContent = character.codepoint;
    values[1].textContent = character.name;
    values[2].textContent = character.glyph;
    values[3].textContent = `${character.script} / ${character.block}`;
  };

  data.characters.forEach((character) => {
    const button = document.createElement("button");
    button.className = "glyph-card";
    button.type = "button";
    button.tabIndex = -1;
    button.setAttribute("aria-pressed", "false");
    button.setAttribute(
      "aria-label",
      `${character.codepoint}, ${character.name}, glyph ${character.glyph}`,
    );
    button.dataset.script = character.script;
    button.dataset.search = normalise(
      [
        character.character,
        character.display,
        character.codepoint,
        character.codepoint.replace("+", ""),
        character.name,
        character.glyph,
        character.script,
        character.block,
        character.category,
      ].join(" "),
    );

    const glyph = document.createElement("span");
    glyph.className = "glyph-char";
    glyph.textContent = character.display;
    const code = document.createElement("span");
    code.className = "glyph-code";
    code.textContent = character.codepoint;
    const name = document.createElement("span");
    name.className = "glyph-name";
    name.textContent = character.name;
    button.append(glyph, code, name);
    button.addEventListener("click", () => showCharacter(character, button));
    button.addEventListener("keydown", (event) => {
      if (
        !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(
          event.key,
        )
      ) {
        return;
      }
      event.preventDefault();
      const visibleButtons = characterButtons.filter((item) => !item.hidden);
      const currentIndex = visibleButtons.indexOf(button);
      const columns = getComputedStyle(glyphGrid).gridTemplateColumns.split(" ").length;
      const movement = {
        ArrowLeft: -1,
        ArrowRight: 1,
        ArrowUp: -columns,
        ArrowDown: columns,
        Home: -currentIndex,
        End: visibleButtons.length - currentIndex - 1,
      }[event.key];
      const nextIndex = clamp(
        currentIndex + movement,
        0,
        visibleButtons.length - 1,
      );
      const nextButton = visibleButtons[nextIndex];
      const characterIndex = characterButtons.indexOf(nextButton);
      showCharacter(data.characters[characterIndex], nextButton);
      nextButton.focus();
    });
    characterButtons.push(button);
    glyphGrid.append(button);
  });

  const filterCharacters = () => {
    const query = normalise(characterSearch.value.trim());
    const script = scriptFilter.value;
    let visible = 0;
    characterButtons.forEach((button) => {
      const matches =
        (!query || button.dataset.search.includes(query)) &&
        (!script || button.dataset.script === script);
      button.hidden = !matches;
      if (matches) {
        visible += 1;
      }
    });
    characterCount.value = visible;
    characterCount.textContent = `${formatNumber.format(visible)} / ${formatNumber.format(
      data.encodedCount,
    )}`;
    characterEmpty.hidden = visible !== 0;
    if (visible && selectedCharacterButton.hidden) {
      const firstVisibleIndex = characterButtons.findIndex((button) => !button.hidden);
      showCharacter(
        data.characters[firstVisibleIndex],
        characterButtons[firstVisibleIndex],
      );
    }
  };

  characterSearch.addEventListener("input", filterCharacters);
  scriptFilter.addEventListener("change", filterCharacters);
  const initialCharacterIndex = data.characters.findIndex(
    (character) => character.codepoint === "U+0041",
  );
  const safeInitialCharacterIndex = Math.max(0, initialCharacterIndex);
  showCharacter(
    data.characters[safeInitialCharacterIndex],
    characterButtons[safeInitialCharacterIndex],
  );

  const unencodedGlyphs = document.querySelector("#unencoded-glyphs");
  data.unencodedGlyphs.forEach((glyphName) => {
    const item = document.createElement("li");
    item.textContent = glyphName;
    unencodedGlyphs.append(item);
  });
  setText(
    "[data-unencoded-count]",
    `${formatNumber.format(data.unencodedGlyphs.length)} glyph names`,
  );

  const languageStats = document.querySelector("[data-language-stats]");
  ["Latin", "Cyrillic", "Greek"].forEach((script) => {
    const card = document.createElement("article");
    const count = document.createElement("strong");
    count.textContent = formatNumber.format(data.languageSummary[script] ?? 0);
    const label = document.createElement("span");
    label.textContent = `${script} language profiles`;
    card.append(count, label);
    languageStats.append(card);
  });

  const languageSearch = document.querySelector("#language-search");
  const languageCount = document.querySelector("#language-count");
  const languageGroups = document.querySelector("#language-groups");
  const languageEmpty = document.querySelector("#language-empty");

  const renderLanguages = () => {
    const query = normalise(languageSearch.value.trim());
    const filtered = data.languages.filter((language) =>
      normalise(
        [
          language.name,
          language.autonym,
          language.iso,
          language.script,
        ].join(" "),
      ).includes(query),
    );
    const groups = new Map();
    filtered.forEach((language) => {
      if (!groups.has(language.script)) {
        groups.set(language.script, []);
      }
      groups.get(language.script).push(language);
    });

    languageGroups.replaceChildren();
    ["Latin", "Cyrillic", "Greek"].forEach((script) => {
      const languages = groups.get(script);
      if (!languages?.length) {
        return;
      }
      const section = document.createElement("section");
      section.className = "language-group";
      const heading = document.createElement("h3");
      heading.textContent = script;
      const count = document.createElement("span");
      count.textContent = formatNumber.format(languages.length);
      heading.append(count);

      const list = document.createElement("ul");
      list.className = "language-list";
      languages.forEach((language) => {
        const item = document.createElement("li");
        const name = document.createElement("b");
        name.textContent = language.name;
        const detail = document.createElement("span");
        detail.textContent = language.autonym
          ? `${language.autonym} · ${language.iso}`
          : language.iso;
        item.append(name, detail);
        list.append(item);
      });
      section.append(heading, list);
      languageGroups.append(section);
    });

    languageCount.value = filtered.length;
    languageCount.textContent = `${formatNumber.format(
      filtered.length,
    )} / ${formatNumber.format(data.languageCount)}`;
    languageEmpty.hidden = filtered.length !== 0;
  };

  languageSearch.addEventListener("input", renderLanguages);
  renderLanguages();

  const metricValues = document.querySelector("#metric-values");
  [
    ["Units per em", data.metrics.unitsPerEm],
    ["Monospace advance", data.metrics.advanceWidth],
    ["Cap height", data.metrics.capHeight],
    ["x-height", data.metrics.xHeight],
    ["Typo ascender / descender", `${data.metrics.typoAscender} / ${data.metrics.typoDescender}`],
    ["hhea ascender / descender", `${data.metrics.hheaAscender} / ${data.metrics.hheaDescender}`],
    ["Win ascender / descender", `${data.metrics.winAscender} / ${data.metrics.winDescender}`],
    ["Line gap", data.metrics.typoLineGap],
    ["Font bounding box", `${data.metrics.yMin}…${data.metrics.yMax}`],
    ["Underline position / thickness", `${data.metrics.underlinePosition} / ${data.metrics.underlineThickness}`],
    ["Fixed pitch", data.metrics.fixedPitch ? "true" : "false"],
    ["Use typo metrics", data.metrics.useTypoMetrics ? "true" : "false"],
  ].forEach(([label, value]) => {
    const row = document.createElement("tr");
    const heading = document.createElement("th");
    heading.scope = "row";
    heading.textContent = label;
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(heading, cell);
    metricValues.append(row);
  });

  const formatBytes = (bytes) => {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`;
  };

  const tableValues = document.querySelector("#table-values");
  Object.entries(data.tableSizes).forEach(([tag, bytes]) => {
    const row = document.createElement("tr");
    const heading = document.createElement("th");
    heading.scope = "row";
    const code = document.createElement("code");
    code.textContent = tag;
    heading.append(code);
    const size = document.createElement("td");
    size.textContent = formatBytes(bytes);
    row.append(heading, size);
    tableValues.append(row);
  });
  setText(
    "[data-table-count]",
    `${formatNumber.format(Object.keys(data.tableSizes).length)} tables`,
  );

  const fileValues = document.querySelector("#file-values");
  data.files.forEach((file) => {
    const row = document.createElement("tr");
    const pathCell = document.createElement("td");
    const link = document.createElement("a");
    link.href = `./${file.path}`;
    link.download = "";
    link.textContent = file.path;
    pathCell.append(link);

    const useCell = document.createElement("td");
    useCell.textContent = `${file.kind}${file.variable ? " · variable" : " · static"}`;
    const formatCell = document.createElement("td");
    formatCell.textContent = file.format;
    const sizeCell = document.createElement("td");
    sizeCell.textContent = formatBytes(file.bytes);
    const hashCell = document.createElement("td");
    hashCell.textContent = file.sha256;
    row.append(pathCell, useCell, formatCell, sizeCell, hashCell);
    fileValues.append(row);
  });

  const copyStatus = document.querySelector("#copy-status");
  let copyStatusTimer;
  const announceCopy = (message) => {
    window.clearTimeout(copyStatusTimer);
    copyStatus.textContent = message;
    copyStatus.classList.add("visible");
    copyStatusTimer = window.setTimeout(() => {
      copyStatus.classList.remove("visible");
    }, 1600);
  };

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const fallback = document.createElement("textarea");
    fallback.value = text;
    fallback.setAttribute("readonly", "");
    fallback.style.position = "fixed";
    fallback.style.opacity = "0";
    document.body.append(fallback);
    fallback.select();
    document.execCommand("copy");
    fallback.remove();
  };

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const source = document.getElementById(button.dataset.copy);
      try {
        await copyText(source.innerText);
        announceCopy("Code copied");
      } catch {
        announceCopy("Copy unavailable — select the code manually");
      }
    });
  });

  document.body.dataset.specimenReady = "true";
})();
