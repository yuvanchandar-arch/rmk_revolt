import React, { useState, useEffect, useRef } from "react";

// Mock/Initial Data for LOTUS Demonstration
const INITIAL_LOTS = [
  { id: "LOT-NOMINAL-NMC-200", type: "nominal", size: 200, chemistry: "NMC", format: "pouch", savings: 65.9, status: "CALIBRATED", risk: 0.0499 },
  { id: "LOT-MIXEDAGE-200", type: "mixed_age", size: 200, chemistry: "NMC", format: "cylindrical", savings: 68.4, status: "CALIBRATED", risk: 0.0499 },
  { id: "LOT-CROSSDATASET-200", type: "cross_dataset", size: 200, chemistry: "Mixed", format: "mixed", savings: 62.1, status: "SPLIT_REQUIRED", risk: 0.0499 },
  { id: "BATCH-MIXED-200", type: "mixed_chemistry", size: 200, chemistry: "NMC+LFP", format: "mixed", savings: 0.0, status: "PROVENANCE_ALERT", risk: 0.0500 },
];

export default function App() {
  const getInitialTab = () => {
    if (typeof window !== "undefined" && window.location.hash) {
      const h = window.location.hash.replace("#", "");
      if (["overview", "registry", "calibration", "analytics", "certificate", "shift-demo", "emat-physics"].includes(h)) {
        return h;
      }
    }
    return "overview";
  };

  const [activeTab, setActiveTabState] = useState(getInitialTab);

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    if (typeof window !== "undefined") {
      window.location.hash = tab;
    }
  };

  useEffect(() => {
    const onHashChange = () => {
      const h = window.location.hash.replace("#", "");
      if (["overview", "registry", "calibration", "analytics", "certificate", "shift-demo", "emat-physics"].includes(h)) {
        setActiveTabState(h);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const [activeLot, setActiveLot] = useState("LOT-NOMINAL-NMC-200");
  const [lotUnits, setLotUnits] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [collectionFilter, setCollectionFilter] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;
  
  // Analytics sub-section
  const [analyticsSection, setAnalyticsSection] = useState("throughput");
  const [throughputFilterDay, setThroughputFilterDay] = useState("All");

  // Reference unit selection for Stage-3 Viewer
  const [selectedRefUnit, setSelectedRefUnit] = useState("U001");

  // Unit Inspection Modal
  const [inspectedUnit, setInspectedUnit] = useState(null);

  // Shifted-Lot Demo Segregation state
  const [isShiftSegregated, setIsShiftSegregated] = useState(false);

  // Interactive Live Screening Animation
  const [isScreeningRunning, setIsScreeningRunning] = useState(false);
  const [screeningProgress, setScreeningProgress] = useState(0);

  // Interactive Live Validation Sweep (E0-E5)
  const [isValidationRunning, setIsValidationRunning] = useState(false);
  const [validationProgress, setValidationProgress] = useState(0);
  const [validationStatusText, setValidationStatusText] = useState("");

  // Copy Verification Hash Feedback
  const [copyFeedback, setCopyFeedback] = useState(false);

  // Interactive Test-Time Sweep Slider (m in [15, 100])
  const [mSweepValue, setMSweepValue] = useState(45);

  // Interactive OOD Anomaly Injection Toggle
  const [syntheticOodActive, setSyntheticOodActive] = useState(false);

  // Interactive Lifecycle Tier Preview
  const [activeAppTier, setActiveAppTier] = useState("solar");

  // EMAT Simulator States
  const [degradationState, setDegradationState] = useState("Healthy");
  const [noiseLevel, setNoiseLevel] = useState(0.20);
  const [pulseCount, setPulseCount] = useState(16);
  const canvasRef = useRef(null);

  // Generate 200 mock units on load matching the audited resolved partition
  useEffect(() => {
    const units = [];
    for (let i = 1; i <= 200; i++) {
      const isRef = i <= 45;
      let stage = "Stage 1 Fast Pass";
      let decision = "approve";
      let dcir = 18.5 + (i * 0.08);
      let fade = 8.2 + (i * 0.11);
      let tof = 4.85 + (i * 0.003);
      let mahalanobis = (1.2 + (i * 0.006)).toFixed(2);

      if (isRef) {
        stage = "Stage 3 Reference Sample";
        decision = "approve";
        fade = 8.0 + (i * 0.06);
        dcir = 18.0 + (i * 0.05);
      } else if (i <= 87) { // 42 units: Stage 1 Approved (46..87)
        stage = "Stage 1 Fast Pass";
        decision = "approve";
        fade = 8.5 + (i * 0.04);
        dcir = 19.0 + (i * 0.06);
      } else if (i <= 92) { // 5 units: Stage 1 Rejected (88..92)
        stage = "Stage 1 Screened Out";
        decision = "reject";
        fade = 28.0 + (i * 0.1);
        dcir = 42.0 + (i * 0.15);
      } else if (i <= 123) { // 31 units: Stage 2 Approved (93..123)
        stage = "Stage 2 Kinetic Pass";
        decision = "approve";
        fade = 12.0 + (i * 0.05);
        dcir = 22.0 + (i * 0.08);
      } else if (i <= 192) { // 69 units: Stage 2 Rejected (124..192)
        stage = "Stage 2 Kinetic Rejected";
        decision = "reject";
        fade = 24.0 + (i * 0.06);
        dcir = 34.0 + (i * 0.12);
      } else if (i <= 196) { // 4 units: Stage 3 Fallback Pass (193..196)
        stage = "Stage 3 Fallback Pass";
        decision = "approve";
        fade = 14.2 + (i * 0.03);
        dcir = 24.5 + (i * 0.05);
      } else { // 4 units: Stage 3 Fallback Fail (197..200)
        stage = "Stage 3 Fallback Fail";
        decision = "reject";
        fade = 26.5 + (i * 0.04);
        dcir = 36.5 + (i * 0.08);
      }

      units.push({
        unitId: `U${String(i).padStart(3, "0")}`,
        lotId: activeLot,
        chemistry: activeLot.includes("LFP") ? (i > 140 ? "LFP" : "NMC") : "NMC",
        format: "pouch",
        capacityFade: fade.toFixed(1),
        cycleCount: 200 + i * 5,
        dcir: dcir.toFixed(1),
        tof: tof.toFixed(3),
        decision: decision,
        stage: stage,
        mahalanobis: mahalanobis,
        echoAmp: (0.62 - (fade * 0.012)).toFixed(3),
        waveVelocity: (2850 - (fade * 14.2)).toFixed(0),
        skinDepthRatio: (1.02 + (dcir * 0.008)).toFixed(3),
        seiThicknessProxy: (12.4 + (fade * 0.8)).toFixed(1),
        relaxationSlope: (-1.82 - (dcir * 0.03)).toFixed(2),
        coulombicEff: (99.85 - (fade * 0.04)).toFixed(2),
        tempDelta: (1.2 + (dcir * 0.04)).toFixed(1),
        risk: isRef ? 0.0 : 0.0499,
        isReference: isRef,
        application: decision === "approve" ? "Stationary Solar Backup" : "Recycle Stream"
      });
    }
    setLotUnits(units);
  }, [activeLot]);

  // EMAT Canvas Animation
  useEffect(() => {
    if (activeTab !== "emat-physics") return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animationFrameId;
    let wavePos = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;

      // 1. EMAT Transducer Assembly (left)
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(10, 30, 80, h - 60);
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2;
      ctx.strokeRect(10, 30, 80, h - 60);
      ctx.fillStyle = "#38bdf8";
      ctx.font = "bold 11px Inter, sans-serif";
      ctx.fillText("EMAT COIL", 18, 55);
      ctx.fillText("& MAGNETS", 18, 72);

      // 2. Aluminum Casing with Eddy Current Skin-Depth Glow
      ctx.fillStyle = "#64748b";
      ctx.fillRect(95, 30, 35, h - 60);
      const eddyGrad = ctx.createLinearGradient(95, 0, 130, 0);
      eddyGrad.addColorStop(0, "rgba(56, 189, 248, 0.7)");
      eddyGrad.addColorStop(1, "rgba(56, 189, 248, 0.05)");
      ctx.fillStyle = eddyGrad;
      ctx.fillRect(95, 30, 35, h - 60);
      ctx.fillStyle = "#ffffff";
      ctx.font = "10px Inter, sans-serif";
      ctx.fillText("Al Casing", 97, h - 40);

      // 3. Electrode Stack Bulk
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(135, 30, 260, h - 60);
      ctx.strokeStyle = "#334155";
      ctx.strokeRect(135, 30, 260, h - 60);
      ctx.fillStyle = "#94a3b8";
      ctx.fillText("Electrode Bulk Medium (3.2 mm)", 180, 55);

      // 4. Dynamic Defect Layer (Lithium Plating / SEI)
      let defectW = 0;
      if (degradationState === "Mild") defectW = 10;
      if (degradationState === "Moderate") defectW = 20;
      if (degradationState === "Plating-associated") defectW = 38;
      if (degradationState === "Severe") defectW = 60;

      if (defectW > 0) {
        ctx.fillStyle = degradationState === "Plating-associated" ? "#f59e0b" : "#ef4444";
        ctx.fillRect(395, 30, defectW, h - 60);
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px Inter, sans-serif";
        ctx.fillText(`Defect (${defectW}μm)`, 398, h - 40);
      }

      // 5. Separator & Cathode Stack
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(395 + defectW, 30, w - 410 - defectW, h - 60);
      ctx.strokeStyle = "#475569";
      ctx.strokeRect(395 + defectW, 30, w - 410 - defectW, h - 60);
      ctx.fillStyle = "#94a3b8";
      ctx.fillText("Separator & Current Collector", 410 + defectW, 55);

      // Animated Acoustic Wave Packet
      wavePos = (wavePos + 3) % (w - 120);
      const waveX = 100 + wavePos;
      const waveGrad = ctx.createRadialGradient(waveX, h / 2, 2, waveX, h / 2, 40);
      waveGrad.addColorStop(0, "rgba(56, 189, 248, 0.95)");
      waveGrad.addColorStop(0.5, "rgba(2, 132, 199, 0.4)");
      waveGrad.addColorStop(1, "rgba(2, 132, 199, 0)");
      ctx.fillStyle = waveGrad;
      ctx.fillRect(waveX - 40, 30, 80, h - 60);

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [activeTab, degradationState]);

  // Real File Download Helper (Blob Download)
  const downloadBlob = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 1. Export Certificate JSON Handler
  const handleExportCertificateJson = () => {
    const certData = {
      certificate_id: "CERT-LOTUS-2026-NMC-0499",
      standard: "LOTUS Section 5.8 High-Assurance Lot Qualification Record",
      generated_at: new Date().toISOString(),
      lot_metadata: {
        lot_id: activeLot,
        chemistry: "NMC",
        format: "pouch",
        nominal_capacity_ah: 2.5,
        total_lot_size_N: 200,
        reference_sample_size_m: 45
      },
      statistical_guarantee: {
        methodology: "Learn-Then-Test Finite-Sample UCB (Angelopoulos et al. 2021)",
        confidence_level: 0.90,
        risk_level_delta: 0.10,
        certified_risk_bound_epsilon: 0.0499,
        risk_bound_description: "Early-Approval Statistical Risk Bound R(lambda, a) <= 4.99%",
        empirical_conditional_failure_rate: 0.00,
        empirical_note: "ESTIMATE ONLY - NOT STATISTICALLY CONTROLLED"
      },
      decision_partition: {
        total_units_evaluated: 200,
        approved_count: 77,
        rejected_count: 78,
        reference_cycler_count: 45,
        unresolved_escalation_count: 0,
        abstained_count: 0
      },
      throughput_and_savings: {
        baseline_cycler_time_hours: 800.0,
        realized_total_time_hours: 272.5,
        hours_saved: 527.5,
        realized_savings_percentage: 65.90
      },
      target_application: {
        tier: "Stationary Solar Backup Storage",
        max_c_rate: 0.5,
        voltage_window: [3.0, 4.15],
        operating_temp_max_c: 40.0
      },
      verification_signature: {
        hash: "0x7f9a2b8e4c1d6a3f0e8b7c9d1a5f3e2b4c8a0d7f",
        compliance: "PASS - Formally Certified"
      }
    };
    downloadBlob(JSON.stringify(certData, null, 2), `LOTUS_Lot_Certificate_${activeLot}.json`, "application/json");
  };

  // 2. Export Qualification Evidence CSV Handler
  const handleExportEvidenceCsv = () => {
    const headers = [
      "unit_id", "lot_id", "chemistry", "format", "capacity_fade_pct", 
      "dcir_mohm", "tof_us", "decision", "stage_resolved", "certified_risk_bound", 
      "mahalanobis_dist", "application_tier"
    ];
    const rows = lotUnits.map(u => [
      u.unitId, u.lotId, u.chemistry, u.format, u.capacityFade,
      u.dcir, u.tof, u.decision, `"${u.stage}"`, u.risk,
      u.mahalanobis, `"${u.application}"`
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    downloadBlob(csvContent, `LOTUS_Qualification_Evidence_${activeLot}.csv`, "text/csv");
  };

  // 3. Export Single Unit Trace CSV Handler
  const handleExportUnitTraceCsv = (unitId) => {
    const headers = ["timestamp_s", "voltage_v", "current_a", "temperature_c", "step_name"];
    const rows = [];
    for (let t = 0; t <= 14400; t += 300) {
      let v = 3.20 + (t / 14400) * 0.95;
      let i = t < 7200 ? 1.25 : (t < 10800 ? 0.40 : 0.0);
      let temp = 24.5 + (t / 14400) * 1.8;
      rows.push([t, v.toFixed(3), i.toFixed(2), temp.toFixed(1), t < 10800 ? "CC_CHARGE" : "RELAXATION"]);
    }
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    downloadBlob(csvContent, `NEWARE_Reference_Trace_${unitId}.csv`, "text/csv");
  };

  // Copy Verification Hash Handler
  const handleCopyHash = () => {
    const hash = "0x7f9a2b8e4c1d6a3f0e8b7c9d1a5f3e2b4c8a0d7f";
    if (navigator.clipboard) {
      navigator.clipboard.writeText(hash).then(() => {
        setCopyFeedback(true);
        setTimeout(() => setCopyFeedback(false), 2000);
      });
    } else {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    }
  };

  // Live Sequential Screening Simulation Handler
  const handleRunScreening = () => {
    if (isScreeningRunning) return;
    setIsScreeningRunning(true);
    setScreeningProgress(0);
    const interval = setInterval(() => {
      setScreeningProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsScreeningRunning(false);
          return 100;
        }
        return prev + 10;
      });
    }, 180);
  };

  // Live Validation Sweep Simulation Handler (E0-E5)
  const handleRunValidationSweep = () => {
    if (isValidationRunning) return;
    setIsValidationRunning(true);
    setValidationProgress(0);
    setValidationStatusText("Initializing E0: Multimodal Proof-of-Concept...");

    const steps = [
      { progress: 16, text: "Verifying E0: Proof-of-Concept (Savings: 65.90%, Safety Violations: 0)... PASS" },
      { progress: 33, text: "Running E1: Retrospective Open Datasets (Oxford, NASA, CALCE)... PASS" },
      { progress: 50, text: "Running E2: Multi-Application Requalification (Solar, Lighting, EV)... PASS" },
      { progress: 67, text: "Running E3: Shift Robustness & Active Calibration Segregation... PASS" },
      { progress: 84, text: "Running E4: EMAT Multiphysics Acoustic Dispersion Modality... PASS" },
      { progress: 100, text: "Running E5: End-to-End System Performance & Bound Verification... ALL PASS (6/6)" }
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        setValidationProgress(steps[currentStep].progress);
        setValidationStatusText(steps[currentStep].text);
        currentStep++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          setIsValidationRunning(false);
        }, 1200);
      }
    }, 450);
  };

  // Filtering for Lot Registry
  const filteredUnits = lotUnits.filter(u => {
    const matchSearch = u.unitId.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        u.chemistry.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        u.decision.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCollection = collectionFilter === "ALL" || u.lotId === collectionFilter;
    return matchSearch && matchCollection;
  });

  const totalPages = Math.ceil(filteredUnits.length / rowsPerPage) || 1;
  const displayedUnits = filteredUnits.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  // Selected Unit Data for NEWARE Viewer
  const currentRefUnitData = lotUnits.find(u => u.unitId === selectedRefUnit) || lotUnits[0] || {
    unitId: "U001", capacityFade: "8.5", dcir: "18.6", tof: "4.850", decision: "approve"
  };

  // Dynamic values for Test-Time Savings Slider
  const projectedHours = (mSweepValue * 4.0) + Math.round(((200 - mSweepValue) * 0.42));
  const projectedSavingsPct = (((800.0 - projectedHours) / 800.0) * 100).toFixed(1);
  const projectedEpsilon = (1 - Math.pow(0.10, 1 / mSweepValue)).toFixed(4);

  return (
    <div className="app-container">
      {/* 1. LEFT ICON RAIL */}
      <aside className="icon-rail" id="left-icon-rail">
        <div className="rail-logo">L</div>
        <nav className="rail-nav">
          <button
            className={`rail-btn ${activeTab === "overview" ? "active" : ""}`}
            title="Operations Overview"
            onClick={() => setActiveTab("overview")}
            id="rail-overview"
          >
            📊
          </button>
          <button
            className={`rail-btn ${activeTab === "registry" ? "active" : ""}`}
            title="Lot Registry"
            onClick={() => setActiveTab("registry")}
            id="rail-registry"
          >
            📋
          </button>
          <button
            className={`rail-btn ${activeTab === "calibration" ? "active" : ""}`}
            title="Lot Detail & Live Calibration"
            onClick={() => setActiveTab("calibration")}
            id="rail-calibration"
          >
            🔬
          </button>
          <button
            className={`rail-btn ${activeTab === "analytics" ? "active" : ""}`}
            title="Analytics & Reports"
            onClick={() => setActiveTab("analytics")}
            id="rail-analytics"
          >
            📈
          </button>
          <button
            className={`rail-btn ${activeTab === "certificate" ? "active" : ""}`}
            title="Lot Certificate Viewer"
            onClick={() => setActiveTab("certificate")}
            id="rail-certificate"
          >
            📜
          </button>
          <button
            className={`rail-btn ${activeTab === "shift-demo" ? "active" : ""}`}
            title="Shifted-Lot Demo"
            onClick={() => setActiveTab("shift-demo")}
            id="rail-shift-demo"
          >
            🔀
          </button>
          <button
            className={`rail-btn ${activeTab === "emat-physics" ? "active" : ""}`}
            title="EMAT Multiphysics Visualizer"
            onClick={() => setActiveTab("emat-physics")}
            id="rail-emat-physics"
          >
            📡
          </button>
        </nav>
        <div className="rail-footer">
          <div className="status-dot-pulse" title="System Status: Calibrated & Operational" />
        </div>
      </aside>

      {/* MAIN VIEWPORT */}
      <main className="main-viewport">
        {/* 2. TOP HEADER & PILL NAV */}
        <header className={`top-header ${activeTab === "registry" || activeTab === "shift-demo" || activeTab === "emat-physics" ? "top-header-dark" : ""}`}>
          <div className="brand-section">
            <span className="brand-title">LOTUS-EMAT</span>
            <span className="brand-sub">Lot-Calibrated Qualification Platform</span>
          </div>

          {/* Pill-shaped Top Nav Buttons */}
          <div className={`pill-nav-group ${activeTab === "registry" || activeTab === "shift-demo" || activeTab === "emat-physics" ? "pill-nav-group-dark" : ""}`}>
            <button
              className={`pill-nav-item ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
              id="top-nav-overview"
            >
              Operations Overview
            </button>
            <button
              className={`pill-nav-item ${activeTab === "registry" ? (activeTab === "registry" ? "pill-nav-item-dark active" : "active") : ""}`}
              onClick={() => setActiveTab("registry")}
              id="top-nav-registry"
            >
              Lot Registry
            </button>
            <button
              className={`pill-nav-item ${activeTab === "calibration" ? "active" : ""}`}
              onClick={() => setActiveTab("calibration")}
              id="top-nav-calibration"
            >
              Lot Detail & Calibration
            </button>
            <button
              className={`pill-nav-item ${activeTab === "analytics" ? "active" : ""}`}
              onClick={() => setActiveTab("analytics")}
              id="top-nav-analytics"
            >
              Analytics & Reports
            </button>
            <button
              className={`pill-nav-item ${activeTab === "certificate" ? "active" : ""}`}
              onClick={() => setActiveTab("certificate")}
              id="top-nav-certificate"
            >
              Certificate Viewer
            </button>
            <button
              className={`pill-nav-item ${activeTab === "shift-demo" ? "pill-nav-item-dark active" : ""}`}
              onClick={() => setActiveTab("shift-demo")}
              id="top-nav-shift-demo"
            >
              Shifted-Lot Demo
            </button>
            <button
              className={`pill-nav-item ${activeTab === "emat-physics" ? "pill-nav-item-dark active" : ""}`}
              onClick={() => setActiveTab("emat-physics")}
              id="top-nav-emat-physics"
            >
              EMAT Physics
            </button>
          </div>

          <div className="header-actions">
            <span className="badge-certified" title="Finite-sample Learn-Then-Test bound">
              CERTIFIED R(λ,a) ≤ 4.99%
            </span>
          </div>
        </header>

        {/* 3. OPERATIONS OVERVIEW */}
        {activeTab === "overview" && (
          <div className="page-body theme-light" id="page-operations-overview">
            <div className="lotus-insight-panel">
              <div className="insight-avatar">✦</div>
              <div>
                <div className="insight-text-headline">LOTUS Qualification Intelligence</div>
                <div className="insight-text-body">
                  Nominal Lot <strong>{activeLot}</strong> qualified in <strong>272.5 hours</strong> vs 800.0 hours full test baseline — <strong>saving 65.90% of qualification time</strong> under finite-sample risk bound <strong>ε ≤ 4.99%</strong> at 90% confidence. Fully resolved via Stage 2 kinetic screening and ground-truth Stage 3 fallback.
                </div>
              </div>
            </div>

            <div className="grid-kpi-4">
              <div className="widget-card">
                <div className="widget-header">
                  <div className="widget-title-group">
                    <span className="widget-icon">⚡</span>
                    <span className="widget-title">Lot Throughput</span>
                  </div>
                  <span className="widget-expand-icon">⤢</span>
                </div>
                <div className="kpi-num">200 / 200</div>
                <div className="kpi-label">Total Units Processed (N=200)</div>
              </div>

              <div className="widget-card">
                <div className="widget-header">
                  <div className="widget-title-group">
                    <span className="widget-icon">⏱️</span>
                    <span className="widget-title">Qualification Time Saved</span>
                  </div>
                  <span className="widget-expand-icon">⤢</span>
                </div>
                <div className="kpi-num" style={{ color: "#10b981" }}>65.90%</div>
                <div className="kpi-label">527.5 Hours Saved vs Full Cycler</div>
              </div>

              <div className="widget-card">
                <div className="widget-header">
                  <div className="widget-title-group">
                    <span className="widget-icon">🎯</span>
                    <span className="widget-title">Reference Sample</span>
                  </div>
                  <span className="widget-expand-icon">⤢</span>
                </div>
                <div className="kpi-num" style={{ color: "#0284c7" }}>m = 45</div>
                <div className="kpi-label">Zero-Violation Sample (ε=0.05, δ=0.10)</div>
              </div>

              <div className="widget-card">
                <div className="widget-header">
                  <div className="widget-title-group">
                    <span className="widget-icon">🛡️</span>
                    <span className="widget-title">Certified Risk Bound</span>
                  </div>
                  <span className="widget-expand-icon">⤢</span>
                </div>
                <div className="kpi-num" style={{ color: "#0369a1" }}>≤ 4.99%</div>
                <div className="kpi-label">Statistically Certified (LTT UCB)</div>
              </div>
            </div>

            <div className="widget-card" style={{ marginBottom: "20px" }}>
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">📈</span>
                  <span className="widget-title">Per-Unit Electrical Fingerprint Distribution (Lot Units 1..200)</span>
                </div>
                <span className="widget-expand-icon">⤢</span>
              </div>
              <div style={{ height: "160px", width: "100%", background: "#f8fafc", borderRadius: "8px", padding: "12px", border: "1px solid #e2e8f0" }}>
                <svg width="100%" height="100%" viewBox="0 0 800 140" preserveAspectRatio="none">
                  <line x1="0" y1="35" x2="800" y2="35" stroke="#e2e8f0" strokeDasharray="4" />
                  <line x1="0" y1="70" x2="800" y2="70" stroke="#e2e8f0" strokeDasharray="4" />
                  <line x1="0" y1="105" x2="800" y2="105" stroke="#e2e8f0" strokeDasharray="4" />
                  <polyline
                    fill="none"
                    stroke="#0284c7"
                    strokeWidth="2.5"
                    points="0,110 80,105 160,98 240,92 320,84 400,75 480,62 560,50 640,38 720,28 800,20"
                  />
                  <polyline
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2.5"
                    points="0,30 80,34 160,39 240,45 320,53 400,64 480,78 560,92 640,105 720,115 800,125"
                  />
                </svg>
              </div>
              <div style={{ display: "flex", gap: "20px", marginTop: "10px", fontSize: "0.78rem", color: "#64748b" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ width: "12px", height: "4px", background: "#0284c7" }} /> DC Internal Resistance Proxy (mΩ)</span>
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ width: "12px", height: "4px", background: "#10b981" }} /> Voltage Relaxation Curve Slope</span>
              </div>
            </div>

            <div className="widget-card">
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">🍩</span>
                  <span className="widget-title">Sequential Decision Breakdown (Audited Resolved Partition)</span>
                </div>
                <span className="widget-expand-icon">⤢</span>
              </div>
              <div className="donut-cluster-grid">
                <div className="donut-card">
                  <div className="donut-circle-wrap">
                    <svg viewBox="0 0 36 36" width="72" height="72">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="4" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831" fill="none" stroke="#10b981" strokeWidth="4" strokeDasharray="38.5, 100" />
                    </svg>
                    <div className="donut-count" style={{ color: "#10b981" }}>77</div>
                  </div>
                  <div className="donut-tag" style={{ color: "#10b981" }}>Approved</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Stage 1: 42 | S2: 31 | S3: 4</div>
                </div>

                <div className="donut-card">
                  <div className="donut-circle-wrap">
                    <svg viewBox="0 0 36 36" width="72" height="72">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="4" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831" fill="none" stroke="#0284c7" strokeWidth="4" strokeDasharray="22.5, 100" />
                    </svg>
                    <div className="donut-count" style={{ color: "#0284c7" }}>45</div>
                  </div>
                  <div className="donut-tag" style={{ color: "#0284c7" }}>Reference (m)</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Stage 3 Ground Truth (m=45)</div>
                </div>

                <div className="donut-card">
                  <div className="donut-circle-wrap">
                    <svg viewBox="0 0 36 36" width="72" height="72">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="4" />
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831" fill="none" stroke="#ef4444" strokeWidth="4" strokeDasharray="39.0, 100" />
                    </svg>
                    <div className="donut-count" style={{ color: "#ef4444" }}>78</div>
                  </div>
                  <div className="donut-tag" style={{ color: "#ef4444" }}>Rejected</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Stage 1: 5 | S2: 69 | S3: 4</div>
                </div>

                <div className="donut-card">
                  <div className="donut-circle-wrap">
                    <svg viewBox="0 0 36 36" width="72" height="72">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="4" />
                    </svg>
                    <div className="donut-count" style={{ color: "#8b5cf6" }}>0</div>
                  </div>
                  <div className="donut-tag" style={{ color: "#8b5cf6" }}>Unresolved</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b" }}>100% Pipeline Resolution</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 4. LOT REGISTRY */}
        {activeTab === "registry" && (
          <div className="page-body theme-dark" id="page-lot-registry">
            <div className="widget-card widget-card-dark">
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">📋</span>
                  <span className="widget-title">Lot Registry & Unit Database (Click any row to inspect cell)</span>
                </div>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn-primary-action"
                    onClick={handleExportEvidenceCsv}
                    id="btn-export-registry-csv"
                  >
                    📥 Export Registry CSV
                  </button>
                </div>
              </div>

              {/* Toolbar */}
              <div className="table-toolbar">
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <label style={{ fontSize: "0.78rem", color: "#94a3b8" }}>Select Collection:</label>
                  <select
                    className="collection-select"
                    value={collectionFilter}
                    onChange={(e) => { setCollectionFilter(e.target.value); setCurrentPage(1); }}
                    id="collection-filter-select"
                  >
                    <option value="ALL">All Lots ({INITIAL_LOTS.length})</option>
                    {INITIAL_LOTS.map(l => (
                      <option key={l.id} value={l.id}>{l.id} ({l.chemistry})</option>
                    ))}
                  </select>
                </div>

                <input
                  type="text"
                  className="search-input"
                  placeholder="Quick-search unit ID, chemistry, decision..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                  id="table-quick-search-box"
                />
              </div>

              {/* Dense Table */}
              <div className="dense-table-container">
                <table className="dense-table">
                  <thead>
                    <tr>
                      <th>Unit ID</th>
                      <th>Lot ID</th>
                      <th>Chemistry</th>
                      <th>Stage Path</th>
                      <th>Cap Fade</th>
                      <th>DCIR</th>
                      <th>ToF (μs)</th>
                      <th>Decision</th>
                      <th>Risk Bound</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedUnits.map((u) => (
                      <tr 
                        key={u.unitId} 
                        className="clickable-row"
                        onClick={() => setInspectedUnit(u)}
                        title="Click to view detailed multimodal parameters"
                      >
                        <td style={{ fontWeight: 700, color: "#38bdf8" }}>{u.unitId} {u.isReference ? "★ (Ref)" : ""}</td>
                        <td>{u.lotId}</td>
                        <td>{u.chemistry}</td>
                        <td style={{ fontSize: "0.74rem", color: "#cbd5e1" }}>{u.stage}</td>
                        <td>{u.capacityFade}%</td>
                        <td>{u.dcir} mΩ</td>
                        <td>{u.tof}</td>
                        <td>
                          <span className={`status-pill status-${u.decision}`}>
                            {u.decision}
                          </span>
                        </td>
                        <td>
                          <span className="badge-certified" style={{ fontSize: "0.7rem", padding: "2px 6px" }}>
                            {u.isReference ? "GROUND TRUTH" : "≤ 4.99%"}
                          </span>
                        </td>
                        <td>
                          <button
                            style={{ padding: "4px 8px", background: "rgba(56, 189, 248, 0.15)", border: "1px solid #38bdf8", color: "#38bdf8", borderRadius: "4px", fontSize: "0.72rem", cursor: "pointer", fontWeight: 600 }}
                            onClick={(e) => { e.stopPropagation(); setInspectedUnit(u); }}
                          >
                            Inspect 🔍
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="pagination-bar">
                <span>
                  Showing {Math.min(filteredUnits.length, (currentPage - 1) * rowsPerPage + 1)}–{Math.min(filteredUnits.length, currentPage * rowsPerPage)} of {filteredUnits.length} units
                </span>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    className="btn-page"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    id="btn-prev-page"
                  >
                    Previous
                  </button>
                  <span>Page {currentPage} of {totalPages}</span>
                  <button
                    className="btn-page"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    id="btn-next-page"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 5. LOT DETAIL & LIVE CALIBRATION */}
        {activeTab === "calibration" && (
          <div className="page-body theme-light" id="page-lot-calibration">
            {/* Interactive Screening Control Card */}
            <div className="widget-card" style={{ marginBottom: "20px" }}>
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">⚡</span>
                  <span className="widget-title">Sequential Screening & In-Lot Calibration Engine</span>
                </div>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn-primary-action"
                    onClick={handleRunScreening}
                    disabled={isScreeningRunning}
                    id="btn-run-screening"
                  >
                    {isScreeningRunning ? `Running Calibration (${screeningProgress}%)...` : "▶ Run Sequential Screening"}
                  </button>
                </div>
              </div>

              {isScreeningRunning && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#64748b", marginBottom: "4px" }}>
                    <span>Processing Remaining N-m (155) Units through Stage 1 & Stage 2...</span>
                    <span style={{ fontWeight: 700, color: "#0284c7" }}>{screeningProgress}%</span>
                  </div>
                  <div className="gauge-meter-bg">
                    <div className="gauge-meter-fill" style={{ width: `${screeningProgress}%`, background: "#0284c7" }} />
                  </div>
                </div>
              )}

              <div className="sampling-widget-container">
                <div className="sample-node-box">
                  <div className="sample-node-title">Total Population (N)</div>
                  <div className="sample-node-count">200</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Nominal EV Pouch Lot</div>
                </div>

                <div className="arrow-flow">
                  <span>➔</span>
                  <span className="arrow-label">Random Draw: m = ⌈ln(δ)/ln(1-ε)⌉</span>
                  <span style={{ fontSize: "0.68rem", color: "#0284c7" }}>Finite-Sample Bound</span>
                </div>

                <div className="sample-node-box" style={{ borderColor: "#10b981" }}>
                  <div className="sample-node-title" style={{ color: "#059669" }}>Reference Sample (m)</div>
                  <div className="sample-node-count" style={{ color: "#10b981" }}>45</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Full Stage-3 Testing</div>
                </div>

                <div className="arrow-flow">
                  <span>➔</span>
                  <span className="arrow-label">Calibrates Cutoff λ*</span>
                  <span style={{ fontSize: "0.68rem", color: "#10b981" }}>Learn-Then-Test</span>
                </div>

                <div className="sample-node-box" style={{ borderColor: "#f59e0b" }}>
                  <div className="sample-node-title" style={{ color: "#d97706" }}>Remaining Units (N-m)</div>
                  <div className="sample-node-count" style={{ color: "#f59e0b" }}>155</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Stage 1/2 Fast Screen</div>
                </div>
              </div>
            </div>

            {/* NEWARE-Style Viewer */}
            <div className="widget-card">
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">⚡</span>
                  <span className="widget-title">Stage-3 Reference Test Viewer (Dual-Axis Profile & Parameter Table)</span>
                </div>
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <label style={{ fontSize: "0.8rem", color: "#64748b" }}>Select Reference Unit:</label>
                  <select
                    value={selectedRefUnit}
                    onChange={(e) => setSelectedRefUnit(e.target.value)}
                    style={{ padding: "4px 8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.82rem" }}
                    id="select-ref-unit"
                  >
                    {lotUnits.slice(0, 45).map(u => (
                      <option key={u.unitId} value={u.unitId}>{u.unitId} (Reference)</option>
                    ))}
                  </select>
                  <button
                    className="btn-secondary-action"
                    onClick={() => handleExportUnitTraceCsv(selectedRefUnit)}
                    id="btn-export-ref-trace"
                  >
                    📥 Export Trace CSV
                  </button>
                </div>
              </div>

              <div className="cycler-viewer-grid">
                <div className="cycler-plot-panel">
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "0.8rem" }}>
                    <span style={{ color: "#38bdf8", fontWeight: 700 }}>Voltage Profile (V) [Primary Axis]</span>
                    <span style={{ color: "#f87171", fontWeight: 700 }}>Current (A) [Secondary Axis]</span>
                  </div>
                  <svg width="100%" height="240" viewBox="0 0 500 240" style={{ background: "#0b0f17", borderRadius: "6px" }}>
                    <polyline
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="2.5"
                      points="10,180 80,140 160,110 240,60 320,55 400,120 490,190"
                    />
                    <polyline
                      fill="none"
                      stroke="#f87171"
                      strokeWidth="2"
                      strokeDasharray="4"
                      points="10,60 80,60 160,60 240,60 320,120 400,120 490,120"
                    />
                  </svg>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "0.75rem", color: "#94a3b8" }}>
                    <span>0h (Rest)</span>
                    <span>1h (CC Charge 0.5C)</span>
                    <span>2h (CV Taper)</span>
                    <span>3h (Rest/Relaxation)</span>
                    <span>4h (Discharge)</span>
                  </div>
                </div>

                <div className="cycler-table-panel">
                  <div style={{ fontWeight: 700, fontSize: "0.88rem", marginBottom: "10px", color: "#0f172a" }}>
                    Extracted Reference Parameters ({currentRefUnitData.unitId})
                  </div>
                  <table style={{ width: "100%", fontSize: "0.8rem", borderCollapse: "collapse" }}>
                    <tbody>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Measured Capacity</td><td style={{ fontWeight: 700 }}>{(2.5 * (1 - currentRefUnitData.capacityFade/100)).toFixed(2)} Ah</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Capacity Fade</td><td style={{ fontWeight: 700, color: "#0284c7" }}>{currentRefUnitData.capacityFade}%</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>DCIR (ΔV/ΔI)</td><td style={{ fontWeight: 700 }}>{currentRefUnitData.dcir} mΩ</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Ultrasonic ToF Shift</td><td style={{ fontWeight: 700 }}>+{((currentRefUnitData.tof - 4.85)).toFixed(3)} μs</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Peak Echo Amplitude</td><td style={{ fontWeight: 700 }}>0.582 V</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Self-Discharge Rate</td><td style={{ fontWeight: 700 }}>0.4 mV/day</td></tr>
                      <tr style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "6px 0", color: "#64748b" }}>Thermal Rise during Pulse</td><td style={{ fontWeight: 700 }}>+1.4 °C</td></tr>
                      <tr><td style={{ padding: "6px 0", color: "#64748b" }}>Stage 3 Ground Truth</td><td style={{ fontWeight: 700, color: "#10b981" }}>PASS (Qualified)</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 6. ANALYTICS & REPORTS */}
        {activeTab === "analytics" && (
          <div className="page-body theme-light" id="page-analytics-reports">
            <div className="analytics-layout">
              {/* Left Sidebar Section Nav */}
              <aside className="analytics-nav">
                <button
                  className={`analytics-nav-item ${analyticsSection === "throughput" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("throughput")}
                  id="nav-section-throughput"
                >
                  Qualification Throughput
                </button>
                <button
                  className={`analytics-nav-item ${analyticsSection === "risk" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("risk")}
                  id="nav-section-risk"
                >
                  Risk Certificate Status
                </button>
                <button
                  className={`analytics-nav-item ${analyticsSection === "savings" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("savings")}
                  id="nav-section-savings"
                >
                  Test-Time Savings
                </button>
                <button
                  className={`analytics-nav-item ${analyticsSection === "safety" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("safety")}
                  id="nav-section-safety"
                >
                  Safety & OOD Flags
                </button>
                <button
                  className={`analytics-nav-item ${analyticsSection === "lifecycle" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("lifecycle")}
                  id="nav-section-lifecycle"
                >
                  Lifecycle & Applications
                </button>
                <button
                  className={`analytics-nav-item ${analyticsSection === "e0-e5" ? "active" : ""}`}
                  onClick={() => setAnalyticsSection("e0-e5")}
                  id="nav-section-e0-e5"
                >
                  E0–E5 Validation Suite
                </button>
              </aside>

              {/* Dynamic Main Content Area based on analyticsSection */}
              <div style={{ flex: 1 }}>
                {/* SUB-SECTION 1: QUALIFICATION THROUGHPUT */}
                {analyticsSection === "throughput" && (
                  <div>
                    <div className="two-stat-row">
                      <div className="stat-box-large">
                        <div style={{ fontSize: "0.8rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                          Certified Risk Bound ε (Finite-Sample LTT)
                        </div>
                        <div style={{ fontSize: "2.1rem", fontWeight: 800, color: "#0284c7", marginTop: "4px" }}>
                          ≤ 4.99%
                        </div>
                        <div style={{ fontSize: "0.82rem", color: "#64748b", marginTop: "4px" }}>
                          Zero violations across 500 calibration draws (1-δ = 90% confidence)
                        </div>
                      </div>

                      <div className="stat-box-large">
                        <div style={{ fontSize: "0.8rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                          Realized Qualification Time Saved
                        </div>
                        <div style={{ fontSize: "2.1rem", fontWeight: 800, color: "#10b981", marginTop: "4px" }}>
                          527.5 Hours (65.90%)
                        </div>
                        <div style={{ fontSize: "0.82rem", color: "#64748b", marginTop: "4px" }}>
                          Total test time: 272.5h vs 800.0h full Stage-3 reference protocol
                        </div>
                      </div>
                    </div>

                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">📊</span>
                          <span className="widget-title">Daily Qualification Throughput by Decision</span>
                        </div>
                        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                          <div style={{ display: "flex", gap: "4px", background: "#f1f5f9", padding: "2px", borderRadius: "6px" }}>
                            {["All", "Mon", "Tue", "Wed", "Thu", "Fri"].map(day => (
                              <button
                                key={day}
                                onClick={() => setThroughputFilterDay(day)}
                                style={{
                                  padding: "4px 8px",
                                  border: "none",
                                  borderRadius: "4px",
                                  fontSize: "0.75rem",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                  background: throughputFilterDay === day ? "#0284c7" : "transparent",
                                  color: throughputFilterDay === day ? "#ffffff" : "#64748b"
                                }}
                              >
                                {day}
                              </button>
                            ))}
                          </div>
                          <button
                            className="btn-primary-action"
                            onClick={handleExportCertificateJson}
                            id="btn-export-cert-json-throughput"
                          >
                            📥 Export Certificate JSON
                          </button>
                          <button
                            className="btn-secondary-action"
                            onClick={handleExportEvidenceCsv}
                            id="btn-export-csv-throughput"
                          >
                            📄 Export CSV
                          </button>
                        </div>
                      </div>

                      <div style={{ height: "180px", display: "flex", alignItems: "flex-end", gap: "24px", padding: "20px 20px 0 20px", borderBottom: "1px solid #e2e8f0" }}>
                        {[
                          { key: "Mon", day: "Day 1 (Mon)", app: 40, esc: 10, rej: 2 },
                          { key: "Tue", day: "Day 2 (Tue)", app: 45, esc: 8, rej: 1 },
                          { key: "Wed", day: "Day 3 (Wed)", app: 38, esc: 14, rej: 3 },
                          { key: "Thu", day: "Day 4 (Thu)", app: 42, esc: 12, rej: 1 },
                          { key: "Fri", day: "Day 5 (Fri)", app: 48, esc: 6, rej: 0 },
                        ]
                        .filter(d => throughputFilterDay === "All" || d.key === throughputFilterDay)
                        .map((d, i) => (
                          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", height: "100%", justifyContent: "flex-end" }}>
                            <div style={{ width: "36px", height: `${d.rej * 6}px`, background: "#ef4444", borderRadius: "4px 4px 0 0" }} title={`Rejected: ${d.rej}`} />
                            <div style={{ width: "36px", height: `${d.esc * 5}px`, background: "#f59e0b" }} title={`Escalated to Stage 2: ${d.esc}`} />
                            <div style={{ width: "36px", height: `${d.app * 2.2}px`, background: "#10b981", borderRadius: "0 0 4px 4px" }} title={`Approved: ${d.app}`} />
                            <span style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "6px" }}>{d.day}</span>
                          </div>
                        ))}
                      </div>
                      <div style={{ display: "flex", gap: "16px", padding: "12px 20px", fontSize: "0.75rem", color: "#64748b" }}>
                        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ width: "10px", height: "10px", background: "#10b981", borderRadius: "2px" }} /> Approved (Stage 1)</span>
                        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ width: "10px", height: "10px", background: "#f59e0b", borderRadius: "2px" }} /> Escalated (Stage 2)</span>
                        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}><span style={{ width: "10px", height: "10px", background: "#ef4444", borderRadius: "2px" }} /> Rejected / Recycle</span>
                      </div>
                    </div>

                    <div className="widget-card">
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">⚡</span>
                          <span className="widget-title">Multimodal vs Unimodal Efficiency Comparison</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "40px", padding: "10px 20px" }}>
                        <div style={{ position: "relative", width: "130px", height: "130px" }}>
                          <svg viewBox="0 0 36 36" width="130" height="130">
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="4.5" />
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831" fill="none" stroke="#0284c7" strokeWidth="4.5" strokeDasharray="65.9, 100" />
                          </svg>
                          <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
                            <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0284c7" }}>65.9%</div>
                            <div style={{ fontSize: "0.68rem", color: "#64748b" }}>Fused Savings</div>
                          </div>
                        </div>

                        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "10px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f1f5f9", paddingBottom: "6px" }}>
                            <span style={{ fontWeight: 600, color: "#0284c7" }}>LOTUS + EMAT Fused Multimodal</span>
                            <span style={{ fontWeight: 800 }}>65.90% Time Savings (272.5h total)</span>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f1f5f9", paddingBottom: "6px" }}>
                            <span style={{ fontWeight: 600, color: "#f59e0b" }}>Electrical-Only Fingerprint</span>
                            <span style={{ fontWeight: 800 }}>52.40% Time Savings (380.8h total)</span>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ fontWeight: 600, color: "#64748b" }}>Full Stage-3 Cycler Baseline</span>
                            <span style={{ fontWeight: 800 }}>0.00% Savings (800.0h total)</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* SUB-SECTION 2: RISK CERTIFICATE STATUS */}
                {analyticsSection === "risk" && (
                  <div>
                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">📜</span>
                          <span className="widget-title">Section 5.8 High-Assurance Lot Qualification Record</span>
                        </div>
                        <div style={{ display: "flex", gap: "10px" }}>
                          <button
                            className="btn-secondary-action"
                            onClick={handleCopyHash}
                            id="btn-copy-hash"
                          >
                            {copyFeedback ? "✓ Copied Hash!" : "📋 Copy Verification Hash"}
                          </button>
                          <button
                            className="btn-primary-action"
                            onClick={handleExportCertificateJson}
                            id="btn-export-cert-json-risk"
                          >
                            📥 Export Certificate JSON
                          </button>
                        </div>
                      </div>

                      <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "18px", marginBottom: "16px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                          <div>
                            <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Certificate Identifier</span>
                            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a" }}>CERT-LOTUS-2026-NMC-0499</div>
                          </div>
                          <span className="status-pill status-approve" style={{ padding: "6px 14px", fontSize: "0.82rem" }}>
                            ✓ VERIFIED & CALIBRATED
                          </span>
                        </div>
                        <div style={{ fontSize: "0.82rem", color: "#64748b", lineHeight: "1.6" }}>
                          • Lot Identifier: <strong>{activeLot}</strong> | Evaluated Cells: <strong>N = 200</strong> | Calibration Sample: <strong>m = 45</strong><br />
                          • Learn-Then-Test Statistical Confidence: <strong>1 - δ = 90.0%</strong> | Finite-Sample Bound: <strong>ε ≤ 4.99%</strong><br />
                          • SHA-256 Audit Digest: <code style={{ color: "#0284c7" }}>0x7f9a2b8e4c1d6a3f0e8b7c9d1a5f3e2b4c8a0d7f</code>
                        </div>
                      </div>

                      {/* Stacked Dual-Risk Display */}
                      <div style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "10px", padding: "16px", marginBottom: "16px" }}>
                        <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center" }}>
                          <div style={{ textAlign: "center" }}>
                            <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                              Statistically Certified Early-Approval Risk
                            </div>
                            <div style={{ marginTop: "6px" }}>
                              <span className="badge-certified" style={{ fontSize: "1.05rem", padding: "6px 16px" }}>
                                CERTIFIED: R(λ, a) ≤ 4.99%
                              </span>
                            </div>
                            <div style={{ fontSize: "0.72rem", color: "#0284c7", marginTop: "4px", fontWeight: 600 }}>
                              Learn-Then-Test UCB (Confidence 1-δ = 90.0%)
                            </div>
                          </div>

                          <div style={{ width: "1px", height: "45px", background: "#cbd5e1" }} />

                          <div style={{ textAlign: "center" }}>
                            <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                              Empirical Conditional Failure Rate
                            </div>
                            <div style={{ marginTop: "6px" }}>
                              <span className="badge-estimate" style={{ fontSize: "1.05rem", padding: "6px 16px" }}>
                                ESTIMATE — NOT CONTROLLED: 0.00%
                              </span>
                            </div>
                            <div style={{ fontSize: "0.72rem", color: "#d97706", marginTop: "4px", fontStyle: "italic" }}>
                              Observed Rate Among Approved Units
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Multi-Application Risk Evaluation Table */}
                      <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a", marginBottom: "8px" }}>
                          Cross-Application Risk Guarantees
                        </div>
                        <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ background: "#f8fafc", textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                              <th style={{ padding: "8px" }}>Application Stream</th>
                              <th style={{ padding: "8px" }}>C-Rate Limit</th>
                              <th style={{ padding: "8px" }}>Certified Bound ε</th>
                              <th style={{ padding: "8px" }}>Approved Units</th>
                              <th style={{ padding: "8px" }}>Risk Disposition</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                              <td style={{ padding: "8px", fontWeight: 600 }}>Stationary Solar Backup</td>
                              <td style={{ padding: "8px" }}>0.5C Continuous</td>
                              <td style={{ padding: "8px", color: "#0284c7", fontWeight: 700 }}>≤ 4.99%</td>
                              <td style={{ padding: "8px" }}>77 / 200</td>
                              <td style={{ padding: "8px" }}><span className="status-pill status-approve">APPROVED</span></td>
                            </tr>
                            <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                              <td style={{ padding: "8px", fontWeight: 600 }}>Autonomous Lighting / DC Microgrid</td>
                              <td style={{ padding: "8px" }}>0.2C Continuous</td>
                              <td style={{ padding: "8px", color: "#10b981", fontWeight: 700 }}>≤ 2.45%</td>
                              <td style={{ padding: "8px" }}>112 / 200</td>
                              <td style={{ padding: "8px" }}><span className="status-pill status-approve">APPROVED</span></td>
                            </tr>
                            <tr>
                              <td style={{ padding: "8px", fontWeight: 600 }}>High-Rate Fast Charge EV</td>
                              <td style={{ padding: "8px" }}>1.5C Peak</td>
                              <td style={{ padding: "8px", color: "#ef4444", fontWeight: 700 }}>&gt; 15.0% (Uncertified)</td>
                              <td style={{ padding: "8px" }}>0 / 200</td>
                              <td style={{ padding: "8px" }}><span className="status-pill status-reject">DISQUALIFIED</span></td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <button
                        className="btn-primary-action"
                        onClick={() => setActiveTab("certificate")}
                        id="btn-goto-cert-sheet"
                      >
                        Open Full Printable Certificate Sheet ➔
                      </button>
                    </div>
                  </div>
                )}

                {/* SUB-SECTION 3: TEST-TIME SAVINGS */}
                {analyticsSection === "savings" && (
                  <div>
                    <div className="grid-kpi-4" style={{ marginBottom: "20px" }}>
                      <div className="widget-card">
                        <div className="kpi-num" style={{ color: "#64748b" }}>800.0 h</div>
                        <div className="kpi-label">Baseline Full Cycler Testing (200 × 4.0h)</div>
                      </div>
                      <div className="widget-card">
                        <div className="kpi-num" style={{ color: "#0284c7" }}>272.5 h</div>
                        <div className="kpi-label">LOTUS-EMAT Total Qualification Time</div>
                      </div>
                      <div className="widget-card">
                        <div className="kpi-num" style={{ color: "#10b981" }}>527.5 h</div>
                        <div className="kpi-label">Net Testing Time Saved per Lot</div>
                      </div>
                      <div className="widget-card">
                        <div className="kpi-num" style={{ color: "#10b981" }}>65.90%</div>
                        <div className="kpi-label">Realized Savings Efficiency Ratio</div>
                      </div>
                    </div>

                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">⏱️</span>
                          <span className="widget-title">Stage Duration Breakdown per Unit & Lot</span>
                        </div>
                      </div>
                      <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                        <thead>
                          <tr style={{ background: "#f8fafc", textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                            <th style={{ padding: "8px" }}>Stage Level</th>
                            <th style={{ padding: "8px" }}>Test Modality</th>
                            <th style={{ padding: "8px" }}>Duration / Cell</th>
                            <th style={{ padding: "8px" }}>Cells Evaluated</th>
                            <th style={{ padding: "8px" }}>Total Time (Hours)</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "8px", fontWeight: 700 }}>Stage 0</td>
                            <td style={{ padding: "8px" }}>Safety & Sensor Veto</td>
                            <td style={{ padding: "8px" }}>5 seconds</td>
                            <td style={{ padding: "8px" }}>200</td>
                            <td style={{ padding: "8px" }}>0.3 h</td>
                          </tr>
                          <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "8px", fontWeight: 700 }}>Stage 1</td>
                            <td style={{ padding: "8px" }}>Multimodal Fingerprint (DCIR + EMAT)</td>
                            <td style={{ padding: "8px" }}>30 seconds</td>
                            <td style={{ padding: "8px" }}>200</td>
                            <td style={{ padding: "8px" }}>1.7 h</td>
                          </tr>
                          <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "8px", fontWeight: 700 }}>Stage 2</td>
                            <td style={{ padding: "8px" }}>Kinetic Screening Profile</td>
                            <td style={{ padding: "8px" }}>600 seconds (10 min)</td>
                            <td style={{ padding: "8px" }}>108</td>
                            <td style={{ padding: "8px" }}>18.0 h</td>
                          </tr>
                          <tr>
                            <td style={{ padding: "8px", fontWeight: 700 }}>Stage 3</td>
                            <td style={{ padding: "8px" }}>Reference Full Test + Ground Truth Fallback</td>
                            <td style={{ padding: "8px" }}>14,400 seconds (4 hours)</td>
                            <td style={{ padding: "8px" }}>45 (Ref) + 8 (Fallback)</td>
                            <td style={{ padding: "8px" }}>252.5 h</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    {/* Interactive Sample Size Sweep Simulator */}
                    <div className="widget-card">
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">🎛️</span>
                          <span className="widget-title">Interactive Reference Sample Size (m) Trade-off Simulator</span>
                        </div>
                      </div>
                      <div style={{ fontSize: "0.82rem", color: "#64748b", marginBottom: "12px" }}>
                        Adjust calibration sample size <strong>m</strong> to evaluate the dynamic trade-off between statistical guarantee sharpness <strong>ε</strong> and realized qualification hours.
                      </div>
                      <div className="slider-control-box">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <span style={{ fontWeight: 700, fontSize: "0.88rem" }}>Selected Sample Size: m = {mSweepValue} cells</span>
                          <span style={{ color: "#0284c7", fontWeight: 800 }}>Projected Savings: {projectedSavingsPct}%</span>
                        </div>
                        <input
                          type="range"
                          min="15"
                          max="100"
                          step="1"
                          value={mSweepValue}
                          onChange={(e) => setMSweepValue(parseInt(e.target.value))}
                          style={{ width: "100%" }}
                          id="slider-m-sweep"
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "#94a3b8", marginTop: "4px" }}>
                          <span>m = 15 (Fastest, ε ≤ 0.142)</span>
                          <span>m = 45 (Nominal Baseline, ε ≤ 0.0499)</span>
                          <span>m = 100 (Tightest, ε ≤ 0.0227)</span>
                        </div>

                        <div className="gauge-meter-bg" style={{ marginTop: "14px" }}>
                          <div className="gauge-meter-fill" style={{ width: `${projectedSavingsPct}%`, background: "#10b981" }} />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "10px", fontSize: "0.78rem" }}>
                          <span>Projected Testing Time: <strong>{projectedHours} hours</strong> (vs 800.0h)</span>
                          <span>Theoretical Bound: <strong>ε ≤ {projectedEpsilon}</strong></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* SUB-SECTION 4: SAFETY & OOD FLAGS */}
                {analyticsSection === "safety" && (
                  <div>
                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">🛡️</span>
                          <span className="widget-title">Hardware Safety Interlocks & OOD Fail-Safe Abstention</span>
                        </div>
                        <button
                          className={syntheticOodActive ? "btn-secondary-action" : "btn-primary-action"}
                          onClick={() => setSyntheticOodActive(!syntheticOodActive)}
                          id="btn-toggle-ood-anomaly"
                        >
                          {syntheticOodActive ? "✓ Reset Synthetic Anomaly" : "⚠️ Simulate / Inject OOD Anomaly"}
                        </button>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px", marginBottom: "16px" }}>
                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700 }}>STAGE 0 THERMAL VETO</div>
                          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#10b981", marginTop: "4px" }}>0 Faults</div>
                          <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Max ΔT = 1.4°C across all units</div>
                        </div>

                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700 }}>MAHALANOBIS THRESHOLD</div>
                          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0284c7", marginTop: "4px" }}>d_M ≤ 5.50</div>
                          <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Empirical centroid distance cutoff</div>
                        </div>

                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700 }}>MAX OBSERVED LOT DISTANCE</div>
                          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: syntheticOodActive ? "#ef4444" : "#10b981", marginTop: "4px" }}>
                            {syntheticOodActive ? "d_M = 12.84" : "d_M = 2.41"}
                          </div>
                          <div style={{ fontSize: "0.72rem", color: "#64748b" }}>
                            {syntheticOodActive ? "Anomaly Flagged in Quarantine" : "Safely In-Distribution"}
                          </div>
                        </div>
                      </div>

                      {syntheticOodActive && (
                        <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444", borderRadius: "8px", padding: "14px", marginBottom: "16px" }}>
                          <div style={{ color: "#ef4444", fontWeight: 700, fontSize: "0.88rem" }}>
                            🚨 Active OOD Anomaly Quarantined: UNIT-OOD-SYNTH-999
                          </div>
                          <div style={{ fontSize: "0.8rem", color: "#334155", marginTop: "4px" }}>
                            Cell exhibits severe interfacial impedance anomaly (Mahalanobis distance 12.84 &gt; threshold 5.50). LOTUS pipeline immediately aborted automated qualification and triggered fail-safe <strong>ABSTAIN (QUARANTINE)</strong>. Zero false approvals committed.
                          </div>
                        </div>
                      )}

                      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a", marginBottom: "8px" }}>
                        Safety & Sensor Quarantine Log
                      </div>
                      <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                        <thead>
                          <tr style={{ background: "#f8fafc", textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
                            <th style={{ padding: "8px" }}>Cell ID</th>
                            <th style={{ padding: "8px" }}>Fault Class</th>
                            <th style={{ padding: "8px" }}>Metric Value</th>
                            <th style={{ padding: "8px" }}>Threshold</th>
                            <th style={{ padding: "8px" }}>System Disposition</th>
                          </tr>
                        </thead>
                        <tbody>
                          {syntheticOodActive && (
                            <tr style={{ background: "rgba(239, 68, 68, 0.05)", borderBottom: "1px solid #f1f5f9" }}>
                              <td style={{ padding: "8px", fontWeight: 700, color: "#ef4444" }}>UNIT-OOD-SYNTH-999</td>
                              <td style={{ padding: "8px" }}>Interfacial Acoustic Delamination</td>
                              <td style={{ padding: "8px", fontWeight: 700 }}>d_M = 12.84</td>
                              <td style={{ padding: "8px" }}>5.50</td>
                              <td style={{ padding: "8px" }}><span className="status-pill status-reject">ABSTAIN (QUARANTINED)</span></td>
                            </tr>
                          )}
                          <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "8px", fontWeight: 600 }}>U088</td>
                            <td style={{ padding: "8px" }}>High DCIR Anomaly (Recycle Stream)</td>
                            <td style={{ padding: "8px" }}>49.8 mΩ</td>
                            <td style={{ padding: "8px" }}>32.0 mΩ</td>
                            <td style={{ padding: "8px" }}><span className="status-pill status-reject">STAGE 1 REJECT</span></td>
                          </tr>
                          <tr>
                            <td style={{ padding: "8px", fontWeight: 600 }}>U198</td>
                            <td style={{ padding: "8px" }}>Accelerated Degradation Knee Detected</td>
                            <td style={{ padding: "8px" }}>27.8% Fade</td>
                            <td style={{ padding: "8px" }}>20.0% Fade</td>
                            <td style={{ padding: "8px" }}><span className="status-pill status-reject">STAGE 3 REJECT</span></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* SUB-SECTION 5: LIFECYCLE & APPLICATIONS */}
                {analyticsSection === "lifecycle" && (
                  <div>
                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">🔄</span>
                          <span className="widget-title">Secondary-Life Reuse Qualification Matrix</span>
                        </div>
                        <div style={{ display: "flex", gap: "6px" }}>
                          {[
                            { id: "solar", label: "Stationary Solar Backup (0.5C)" },
                            { id: "lighting", label: "Autonomous Lighting (0.2C)" },
                            { id: "fast_charge", label: "Fast Charge Buffer (1.5C)" }
                          ].map(t => (
                            <button
                              key={t.id}
                              onClick={() => setActiveAppTier(t.id)}
                              style={{
                                padding: "6px 12px",
                                border: "none",
                                borderRadius: "6px",
                                fontSize: "0.78rem",
                                fontWeight: 700,
                                cursor: "pointer",
                                background: activeAppTier === t.id ? "#0284c7" : "#f1f5f9",
                                color: activeAppTier === t.id ? "#ffffff" : "#64748b"
                              }}
                            >
                              {t.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "14px", marginBottom: "16px" }}>
                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>MAX C-RATE LIMIT</div>
                          <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#0284c7", marginTop: "4px" }}>
                            {activeAppTier === "solar" ? "0.50 C" : (activeAppTier === "lighting" ? "0.20 C" : "1.50 C")}
                          </div>
                          <div style={{ fontSize: "0.7rem", color: "#64748b" }}>Continuous discharge allowance</div>
                        </div>

                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>ALLOWED SOC WINDOW</div>
                          <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#10b981", marginTop: "4px" }}>
                            {activeAppTier === "solar" ? "20% – 85%" : (activeAppTier === "lighting" ? "10% – 90%" : "30% – 80%")}
                          </div>
                          <div style={{ fontSize: "0.7rem", color: "#64748b" }}>Mitigates calendar aging</div>
                        </div>

                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>TEMP LIMIT</div>
                          <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
                            {activeAppTier === "solar" ? "≤ 40.0 °C" : (activeAppTier === "lighting" ? "≤ 45.0 °C" : "≤ 35.0 °C")}
                          </div>
                          <div style={{ fontSize: "0.7rem", color: "#64748b" }}>Active thermal throttle trip</div>
                        </div>

                        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                          <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>CERTIFIED SECONDARY LIFE</div>
                          <div style={{ fontSize: "1.3rem", fontWeight: 800, color: activeAppTier === "fast_charge" ? "#ef4444" : "#10b981", marginTop: "4px" }}>
                            {activeAppTier === "solar" ? "1,850 Cycles" : (activeAppTier === "lighting" ? "2,400 Cycles" : "Disqualified")}
                          </div>
                          <div style={{ fontSize: "0.7rem", color: "#64748b" }}>Until 70% retention cutoff</div>
                        </div>
                      </div>

                      <div style={{ height: "140px", width: "100%", background: "#f8fafc", borderRadius: "8px", padding: "12px", border: "1px solid #e2e8f0" }}>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", marginBottom: "6px" }}>
                          Projected Capacity Retention Trajectory (Secondary Life Cycles 0..2000)
                        </div>
                        <svg width="100%" height="90" viewBox="0 0 600 90" preserveAspectRatio="none">
                          <line x1="0" y1="20" x2="600" y2="20" stroke="#e2e8f0" strokeDasharray="3" />
                          <line x1="0" y1="50" x2="600" y2="50" stroke="#e2e8f0" strokeDasharray="3" />
                          <polyline
                            fill="none"
                            stroke={activeAppTier === "fast_charge" ? "#ef4444" : "#0284c7"}
                            strokeWidth="2.5"
                            points={
                              activeAppTier === "solar"
                                ? "0,15 150,22 300,32 450,46 600,65"
                                : activeAppTier === "lighting"
                                ? "0,12 150,17 300,24 450,33 600,45"
                                : "0,15 100,30 200,55 300,80 400,90"
                            }
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                {/* SUB-SECTION 6: E0–E5 VALIDATION SUITE */}
                {analyticsSection === "e0-e5" && (
                  <div>
                    <div className="widget-card" style={{ marginBottom: "20px" }}>
                      <div className="widget-header">
                        <div className="widget-title-group">
                          <span className="widget-icon">🧪</span>
                          <span className="widget-title">E0–E5 Comprehensive Empirical Validation Suite</span>
                        </div>
                        <button
                          className="btn-primary-action"
                          onClick={handleRunValidationSweep}
                          disabled={isValidationRunning}
                          id="btn-run-validation-sweep"
                        >
                          {isValidationRunning ? "Running Live Verification Sweep..." : "▶ Run Live Validation Sweep"}
                        </button>
                      </div>

                      {isValidationRunning && (
                        <div style={{ marginBottom: "16px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#64748b", marginBottom: "4px" }}>
                            <span>{validationStatusText}</span>
                            <span style={{ fontWeight: 700, color: "#0284c7" }}>{validationProgress}%</span>
                          </div>
                          <div className="gauge-meter-bg">
                            <div className="gauge-meter-fill" style={{ width: `${validationProgress}%`, background: "#10b981" }} />
                          </div>
                        </div>
                      )}

                      <div className="experiment-grid">
                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E0: Multimodal Proof-of-Concept</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Tested on N=200 synthetic batch with realistic degradation. Realized <strong>65.90% time savings</strong> with <strong>0 false approvals</strong> under finite-sample bound ε ≤ 4.99%.
                          </div>
                        </div>

                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E1: Retrospective Open Cycling</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Evaluated across Oxford, NASA, and CALCE cycling repositories. Verified that learn-then-test finite-sample bound holds across all calibration draws.
                          </div>
                        </div>

                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E2: Multi-Application Requalification</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Rigorous boundary partition for Solar (0.5C), Lighting (0.2C), and High-Rate (1.5C). Successfully rejects unfit cells from high-stress streams.
                          </div>
                        </div>

                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E3: Shift Robustness & Active Calibration</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Detects chemistry and batch heterogeneity. Segregates mixed lots into homogeneous sub-lots to prevent statistical exchangeability violation.
                          </div>
                        </div>

                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E4: EMAT Physical Modality Validation</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Digital matched-filter successfully recovers ultrasonic Time-of-Flight and attenuation at SNR down to -15 dB through metallic packaging.
                          </div>
                        </div>

                        <div className="experiment-card">
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 800, color: "#0284c7" }}>E5: End-to-End System Performance</span>
                            <span className="status-pill status-approve">PASS</span>
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
                            Full-pipeline integration audit. 0 unresolved escalations, verifiable cryptographic certificate hash, and complete automated audit trail.
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 7. LOT CERTIFICATE VIEWER */}
        {activeTab === "certificate" && (
          <div className="page-body theme-light" id="page-certificate-viewer">
            <div className="certificate-sheet">
              {/* Header Banner & Action Bar */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "2px solid #e2e8f0", paddingBottom: "18px", marginBottom: "20px" }}>
                <div>
                  <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "#0f172a" }}>
                    LOTUS High-Assurance Battery Lot Certificate
                  </div>
                  <div style={{ fontSize: "0.82rem", color: "#64748b", marginTop: "4px" }}>
                    Formal Evidence Record per Section 5.8 | Lot ID: <strong>{activeLot}</strong>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <button
                    className="btn-primary-action"
                    onClick={handleExportCertificateJson}
                    id="btn-cert-download-json"
                  >
                    📥 Download Certificate JSON
                  </button>
                  <button
                    className="btn-secondary-action"
                    onClick={() => window.print()}
                    id="btn-cert-print-pdf"
                  >
                    🖨️ Print / Export PDF
                  </button>
                  <div className="qr-placeholder" title="Digital Verification Anchor">
                    QR VERIFIED<br />RECORD
                  </div>
                </div>
              </div>

              {/* Stacked Dual-Risk Box */}
              <div style={{ background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "10px", padding: "18px", marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                      Statistically Certified Early-Approval Risk
                    </div>
                    <div style={{ marginTop: "6px" }}>
                      <span className="badge-certified" style={{ fontSize: "1.05rem", padding: "6px 16px" }}>
                        CERTIFIED: R(λ, a) ≤ 4.99%
                      </span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "#0284c7", marginTop: "4px", fontWeight: 600 }}>
                      Learn-Then-Test UCB (Confidence 1-δ = 90.0%)
                    </div>
                  </div>

                  <div style={{ width: "1px", height: "50px", background: "#cbd5e1" }} />

                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                      Empirical Conditional Failure Rate
                    </div>
                    <div style={{ marginTop: "6px" }}>
                      <span className="badge-estimate" style={{ fontSize: "1.05rem", padding: "6px 16px" }}>
                        ESTIMATE — NOT CONTROLLED: 0.00%
                      </span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "#d97706", marginTop: "4px", fontStyle: "italic" }}>
                      Observed Rate Among Approved Units
                    </div>
                  </div>
                </div>
              </div>

              {/* Benchmark Distribution Curve Panel */}
              <div className="benchmark-curve-box">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a" }}>Population Benchmark Distribution</span>
                  <span style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: 700 }}>✓ Within Optimal Secondary-Life Band</span>
                </div>
                <svg width="100%" height="60" viewBox="0 0 400 60" preserveAspectRatio="none">
                  <path d="M 0,55 Q 100,55 150,30 Q 200,5 250,30 Q 300,55 400,55" fill="rgba(2, 132, 199, 0.08)" stroke="#0284c7" strokeWidth="2" />
                  <line x1="230" y1="5" x2="230" y2="55" stroke="#10b981" strokeWidth="3" strokeDasharray="3" />
                  <circle cx="230" cy="18" r="5" fill="#10b981" />
                </svg>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "#64748b" }}>
                  <span>Below Average</span>
                  <span style={{ fontWeight: 700, color: "#10b981" }}>▲ Lot Calibration Centroid (Score = 0.842)</span>
                  <span>Optimal Fleet Tier</span>
                </div>
              </div>

              {/* Evidence Checklist */}
              <div style={{ marginBottom: "24px" }}>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "10px", color: "#0f172a" }}>
                  Qualification Evidence Checklist
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.82rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> Stage 0 Safety & Sensor Veto Passed</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> Stage 1 Electrical Fingerprint Complete</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> EMAT Acoustic Dispersion Modality Complete</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> Mahalanobis OOD Detector Passed</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> Stationary Solar Storage Tier Assigned (0.5C max)</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><span style={{ color: "#10b981", fontWeight: 800 }}>✓</span> Learn-Then-Test Finite-Sample Bound Formally Calibrated</div>
                </div>
              </div>

              {/* Mandatory Non-Safety Certification Seal Area */}
              <div className="cert-seal-block">
                <div className="cert-seal-title">
                  LOTUS-EMAT Decision Support — Not a Safety Certification
                </div>
                <div className="cert-seal-sub">
                  Statistical decision bounds evaluated under Angelopoulos et al. (2021) Learn-Then-Test protocol. Not an automotive pack functional safety approval.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 8. SHIFTED-LOT DEMO */}
        {activeTab === "shift-demo" && (
          <div className="page-body theme-dark" id="page-shifted-lot-demo">
            <div className="widget-card widget-card-dark" style={{ marginBottom: "20px" }}>
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">🔀</span>
                  <span className="widget-title">Covariate & Chemistry Distribution Shift Mitigation</span>
                </div>
                {isShiftSegregated && (
                  <button
                    className="btn-secondary-action"
                    onClick={() => setIsShiftSegregated(false)}
                    id="btn-reset-sublot-split"
                  >
                    Reset to Mixed Batch
                  </button>
                )}
              </div>

              {!isShiftSegregated ? (
                <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid #f59e0b", borderRadius: "8px", padding: "14px 18px", marginBottom: "16px" }}>
                  <div style={{ color: "#f59e0b", fontWeight: 700, fontSize: "0.9rem" }}>
                    ⚠️ Batch Heterogeneity Detected: BATCH-MIXED-200
                  </div>
                  <div style={{ color: "#cbd5e1", fontSize: "0.82rem", marginTop: "4px" }}>
                    Provenance audit discovered mixed cell chemistries (NMC + LFP) and multiple operating fleets within one batch. Calibrating this batch as a single lot would violate exchangeability and cause statistical risk inflation.
                  </div>
                </div>
              ) : (
                <div style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid #10b981", borderRadius: "8px", padding: "14px 18px", marginBottom: "16px" }}>
                  <div style={{ color: "#10b981", fontWeight: 700, fontSize: "0.9rem" }}>
                    ✓ Automated Provenance Audit Completed: Segregation Active
                  </div>
                  <div style={{ color: "#cbd5e1", fontSize: "0.82rem", marginTop: "4px" }}>
                    BATCH-MIXED-200 successfully split into 2 homogeneous sub-lots: <strong>Sub-Lot A (NMC Pouch, N=140)</strong> and <strong>Sub-Lot B (LFP Prismatic, N=60)</strong>. Exchangeability preserved; independent LTT calibration enabled.
                  </div>
                </div>
              )}

              <button
                className="btn-primary-action"
                style={{ padding: "10px 18px", fontSize: "0.85rem" }}
                onClick={() => setIsShiftSegregated(!isShiftSegregated)}
                id="btn-execute-sublot-split"
              >
                {isShiftSegregated ? "✓ Provenance Segregation Active (Click to Toggle)" : "Execute Provenance-Aware Sub-Lot Splitting"}
              </button>
            </div>

            {/* Sub-Lots Display Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="widget-card widget-card-dark">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontWeight: 700, color: "#38bdf8" }}>Sub-Lot A: BATCH-MIXED-200-A</span>
                  <span className="status-pill status-approve">{isShiftSegregated ? "HOMOGENEOUS & SEGREGATED" : "PENDING SPLIT"}</span>
                </div>
                <div style={{ fontSize: "0.82rem", color: "#cbd5e1", lineHeight: "1.6" }}>
                  • Chemistry: <strong>NMC</strong> | Format: <strong>Pouch</strong><br />
                  • Units: <strong>140 cells</strong> (Meets reference requirement m=45)<br />
                  • Calibration Status: {isShiftSegregated ? <strong style={{ color: "#10b981" }}>Calibrated (ε ≤ 4.99%)</strong> : "Awaiting Segregation"}
                </div>
              </div>

              <div className="widget-card widget-card-dark">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontWeight: 700, color: "#38bdf8" }}>Sub-Lot B: BATCH-MIXED-200-B</span>
                  <span className="status-pill status-approve">{isShiftSegregated ? "HOMOGENEOUS & SEGREGATED" : "PENDING SPLIT"}</span>
                </div>
                <div style={{ fontSize: "0.82rem", color: "#cbd5e1", lineHeight: "1.6" }}>
                  • Chemistry: <strong>LFP</strong> | Format: <strong>Prismatic</strong><br />
                  • Units: <strong>60 cells</strong> (Meets reference requirement m=45)<br />
                  • Calibration Status: {isShiftSegregated ? <strong style={{ color: "#10b981" }}>Calibrated (ε ≤ 4.99%)</strong> : "Awaiting Segregation"}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 9. EMAT MULTIPHYSICS VISUALIZER */}
        {activeTab === "emat-physics" && (
          <div className="page-body theme-dark" id="page-emat-visualizer">
            <div className="widget-card widget-card-dark" style={{ marginBottom: "16px" }}>
              <div className="widget-header">
                <div className="widget-title-group">
                  <span className="widget-icon">📡</span>
                  <span className="widget-title">EMAT Acoustic Multiphysics Visualizer (60 FPS Longitudinal Simulation)</span>
                </div>
                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                  <label style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Degradation State:</label>
                  <select
                    value={degradationState}
                    onChange={(e) => setDegradationState(e.target.value)}
                    style={{ background: "#1e293b", color: "#ffffff", border: "1px solid #334155", padding: "4px 10px", borderRadius: "6px", fontSize: "0.82rem" }}
                    id="select-degradation-state"
                  >
                    <option value="Healthy">Healthy (Baseline)</option>
                    <option value="Mild">Mild Degradation</option>
                    <option value="Moderate">Moderate Degradation</option>
                    <option value="Plating-associated">Plating-associated Perturbation</option>
                    <option value="Severe">Severe Interfacial Delamination</option>
                  </select>
                </div>
              </div>

              <canvas
                ref={canvasRef}
                width={850}
                height={260}
                style={{ width: "100%", height: "260px", background: "#030712", borderRadius: "8px", border: "1px solid #1f2937" }}
                id="emat-canvas-renderer"
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="widget-card widget-card-dark">
                <div className="widget-header">
                  <span className="widget-title">Digital Matched-Filter Receiver Controls</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.82rem" }}>
                  <div>
                    <label style={{ color: "#94a3b8" }}>Noise Injection Level (SNR: -15 dB baseline):</label>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={noiseLevel}
                      onChange={(e) => setNoiseLevel(parseFloat(e.target.value))}
                      style={{ width: "100%", marginTop: "4px" }}
                    />
                  </div>
                  <div>
                    <label style={{ color: "#94a3b8" }}>Coherent Pulse Averaging Count (N={pulseCount} pulses):</label>
                    <input
                      type="range"
                      min="1"
                      max="64"
                      step="1"
                      value={pulseCount}
                      onChange={(e) => setPulseCount(parseInt(e.target.value))}
                      style={{ width: "100%", marginTop: "4px" }}
                    />
                  </div>
                </div>
              </div>

              <div className="widget-card widget-card-dark">
                <div className="widget-header">
                  <span className="widget-title">Live Recovered Acoustic Features</span>
                </div>
                <table style={{ width: "100%", fontSize: "0.82rem" }}>
                  <tbody>
                    <tr><td style={{ color: "#94a3b8", padding: "4px 0" }}>Recovered Time-of-Flight (ToF):</td><td style={{ fontWeight: 700, color: "#38bdf8" }}>{degradationState === "Healthy" ? "4.850 μs" : (degradationState === "Plating-associated" ? "5.006 μs" : "5.320 μs")}</td></tr>
                    <tr><td style={{ color: "#94a3b8", padding: "4px 0" }}>Matched-Filter Peak Amplitude:</td><td style={{ fontWeight: 700 }}>{degradationState === "Healthy" ? "0.615 V" : (degradationState === "Plating-associated" ? "0.342 V" : "0.047 V")}</td></tr>
                    <tr><td style={{ color: "#94a3b8", padding: "4px 0" }}>Interfacial Attenuation:</td><td style={{ fontWeight: 700 }}>{degradationState === "Healthy" ? "0.0 dB" : (degradationState === "Plating-associated" ? "-4.1 dB" : "-22.3 dB")}</td></tr>
                    <tr><td style={{ color: "#94a3b8", padding: "4px 0" }}>Post-DSP Output SNR:</td><td style={{ fontWeight: 700, color: "#10b981" }}>{degradationState === "Healthy" ? "+24.2 dB" : "+18.6 dB"}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 10. CELL INSPECTION MODAL */}
      {inspectedUnit && (
        <div className="modal-overlay" onClick={() => setInspectedUnit(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <div style={{ fontSize: "1.15rem", fontWeight: 800, color: "#0f172a" }}>
                  Unit Inspection: {inspectedUnit.unitId} {inspectedUnit.isReference ? "★ (Reference Sample)" : ""}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "2px" }}>
                  Lot: {inspectedUnit.lotId} | Chemistry: {inspectedUnit.chemistry} | Format: {inspectedUnit.format}
                </div>
              </div>
              <button
                style={{ background: "none", border: "none", fontSize: "1.3rem", cursor: "pointer", color: "#64748b" }}
                onClick={() => setInspectedUnit(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#f8fafc", padding: "12px", borderRadius: "8px", marginBottom: "16px" }}>
                <div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>QUALIFICATION STATUS</div>
                  <span className={`status-pill status-${inspectedUnit.decision}`} style={{ fontSize: "0.85rem", padding: "4px 10px", marginTop: "4px", display: "inline-block" }}>
                    {inspectedUnit.decision.toUpperCase()}
                  </span>
                </div>
                <div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>STAGE RESOLUTION PATH</div>
                  <div style={{ fontWeight: 700, color: "#0284c7", fontSize: "0.85rem", marginTop: "4px" }}>
                    {inspectedUnit.stage}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 700 }}>CERTIFIED RISK BOUND</div>
                  <div style={{ fontWeight: 700, color: "#10b981", fontSize: "0.85rem", marginTop: "4px" }}>
                    {inspectedUnit.isReference ? "GROUND TRUTH VERIFIED" : "R(λ, a) ≤ 4.99%"}
                  </div>
                </div>
              </div>

              <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a", marginBottom: "8px" }}>
                13-Parameter Multimodal Feature Extraction Record
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.8rem" }}>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Measured Capacity Fade:</span> <strong>{inspectedUnit.capacityFade}%</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>DC Internal Resistance:</span> <strong>{inspectedUnit.dcir} mΩ</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Ultrasonic Time-of-Flight:</span> <strong>{inspectedUnit.tof} μs</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Matched-Filter Echo Amplitude:</span> <strong>{inspectedUnit.echoAmp} V</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Acoustic Wave Velocity:</span> <strong>{inspectedUnit.waveVelocity} m/s</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Skin-Depth Penetration Ratio:</span> <strong>{inspectedUnit.skinDepthRatio}</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>SEI Layer Thickness Proxy:</span> <strong>{inspectedUnit.seiThicknessProxy} μm</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Voltage Relaxation Slope:</span> <strong>{inspectedUnit.relaxationSlope} mV/s</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Coulombic Efficiency:</span> <strong>{inspectedUnit.coulombicEff}%</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Pulse Thermal Delta (ΔT):</span> <strong>+{inspectedUnit.tempDelta} °C</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Mahalanobis Distance (d_M):</span> <strong>{inspectedUnit.mahalanobis}</strong>
                </div>
                <div style={{ background: "#ffffff", border: "1px solid #f1f5f9", padding: "8px", borderRadius: "6px" }}>
                  <span style={{ color: "#64748b" }}>Assigned Application Stream:</span> <strong>{inspectedUnit.application}</strong>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary-action"
                onClick={() => handleExportUnitTraceCsv(inspectedUnit.unitId)}
              >
                📥 Export Unit Telemetry Trace CSV
              </button>
              <button
                className="btn-primary-action"
                onClick={() => setInspectedUnit(null)}
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
