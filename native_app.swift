import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var textView: NSTextView!
    var regionPopUp: NSPopUpButton!
    var browserPopUp: NSPopUpButton!
    var pLabel: NSTextField!
    var postcodeField: NSTextField!
    var radiusField: NSTextField!
    var intervalField: NSTextField!
    var colorPopUp: NSPopUpButton!
    var check256: NSButton!
    var check512: NSButton!
    var check1tb: NSButton!
    var check2tb: NSButton!
    var checkHourlyHeartbeat: NSButton!
    var modelSummaryLabel: NSTextField!
    var discordField: NSTextField!
    var startBtn: NSButton!
    var statusLabel: NSTextField!
    
    var process: Process?
    var pipe: Pipe?
    var isManualStop = false
    var sleepActivity: NSObjectProtocol?
    
    var resolvedScriptPath: String {
        // 1. Check if packaged directly inside app bundle Resources
        if let bundleResource = Bundle.main.path(forResource: "check_stock", ofType: "py") {
            return bundleResource
        }
        // 2. Check in same directory as the executable
        let execDir = Bundle.main.bundleURL.deletingLastPathComponent().path
        let siblingPath = (execDir as NSString).appendingPathComponent("check_stock.py")
        if FileManager.default.fileExists(atPath: siblingPath) {
            return siblingPath
        }
        // 3. Check current working directory
        let cwd = FileManager.default.currentDirectoryPath
        let cwdPath = (cwd as NSString).appendingPathComponent("check_stock.py")
        if FileManager.default.fileExists(atPath: cwdPath) {
            return cwdPath
        }
        return "check_stock.py"
    }
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        
        let rect = NSRect(x: 100, y: 100, width: 860, height: 720)
        window = NSWindow(
            contentRect: rect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Apple Stock Monitor — Multi-Region (UK & US)"
        window.minSize = NSSize(width: 820, height: 540)
        window.center()
        
        let content = NSView()
        window.contentView = content
        
        // 1. Header
        let title = NSTextField(labelWithString: "🍏 Apple Stock Monitor")
        title.font = NSFont.boldSystemFont(ofSize: 18)
        title.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(title)
        
        let sub = NSTextField(labelWithString: "UK & US Support • Firefox, Safari & Chrome • Multi-Model Search • 100% Vibe-Coded")
        sub.font = NSFont.systemFont(ofSize: 11)
        sub.textColor = .secondaryLabelColor
        sub.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(sub)
        
        // 2. Settings Box (Responsive)
        let box = NSBox()
        box.title = "Search Parameters, Region, Browser & Alerts"
        box.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(box)
        
        let bContent = box.contentView!
        
        // --- Row 1: Region, Browser & Main Controls ---
        let regionLabel = NSTextField(labelWithString: "Region:")
        regionLabel.font = NSFont.boldSystemFont(ofSize: 12)
        regionLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(regionLabel)
        
        regionPopUp = NSPopUpButton(frame: .zero, pullsDown: false)
        regionPopUp.addItems(withTitles: ["🇬🇧 UK (United Kingdom)", "🇺🇸 US (United States)"])
        regionPopUp.target = self
        regionPopUp.action = #selector(regionChanged)
        regionPopUp.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(regionPopUp)
        
        let browserLabel = NSTextField(labelWithString: "Browser:")
        browserLabel.font = NSFont.boldSystemFont(ofSize: 12)
        browserLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(browserLabel)
        
        browserPopUp = NSPopUpButton(frame: .zero, pullsDown: false)
        browserPopUp.addItems(withTitles: ["Firefox", "Safari", "Google Chrome", "Default Browser"])
        browserPopUp.target = self
        browserPopUp.action = #selector(preferenceChanged)
        browserPopUp.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(browserPopUp)
        
        startBtn = NSButton(title: "▶ Start Monitoring", target: self, action: #selector(toggleMonitoring))
        startBtn.bezelStyle = .rounded
        startBtn.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(startBtn)
        
        let testBtn = NSButton(title: "🧪 Test", target: self, action: #selector(runTest))
        testBtn.bezelStyle = .rounded
        testBtn.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(testBtn)
        
        let clearBtn = NSButton(title: "Clear", target: self, action: #selector(clearLogs))
        clearBtn.bezelStyle = .rounded
        clearBtn.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(clearBtn)
        
        // --- Row 2: Location, Radius, Interval & Colour ---
        pLabel = NSTextField(labelWithString: "Postcode:")
        pLabel.font = NSFont.boldSystemFont(ofSize: 12)
        pLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(pLabel)
        
        postcodeField = NSTextField()
        postcodeField.stringValue = "W1B 3AG"
        postcodeField.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(postcodeField)
        
        let rLabel = NSTextField(labelWithString: "Radius:")
        rLabel.font = NSFont.boldSystemFont(ofSize: 12)
        rLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(rLabel)
        
        radiusField = NSTextField()
        radiusField.stringValue = "50"
        radiusField.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(radiusField)
        
        let miLabel = NSTextField(labelWithString: "miles")
        miLabel.textColor = .secondaryLabelColor
        miLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(miLabel)
        
        let iLabel = NSTextField(labelWithString: "Interval:")
        iLabel.font = NSFont.boldSystemFont(ofSize: 12)
        iLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(iLabel)
        
        intervalField = NSTextField()
        intervalField.stringValue = "45"
        intervalField.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(intervalField)
        
        let sLabel = NSTextField(labelWithString: "sec")
        sLabel.textColor = .secondaryLabelColor
        sLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(sLabel)
        
        let colorLabel = NSTextField(labelWithString: "Colour:")
        colorLabel.font = NSFont.boldSystemFont(ofSize: 12)
        colorLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(colorLabel)
        
        colorPopUp = NSPopUpButton(frame: .zero, pullsDown: false)
        colorPopUp.addItems(withTitles: ["Both Colours", "Night Sky", "Star White"])
        colorPopUp.target = self
        colorPopUp.action = #selector(updateModelSummary)
        colorPopUp.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(colorPopUp)
        
        // --- Row 3: Multi-Storage Selection ---
        let storageLabel = NSTextField(labelWithString: "Storage:")
        storageLabel.font = NSFont.boldSystemFont(ofSize: 12)
        storageLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(storageLabel)
        
        check256 = NSButton(checkboxWithTitle: "256GB", target: self, action: #selector(updateModelSummary))
        check256.state = .on
        check256.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(check256)
        
        check512 = NSButton(checkboxWithTitle: "512GB", target: self, action: #selector(updateModelSummary))
        check512.state = .on
        check512.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(check512)
        
        check1tb = NSButton(checkboxWithTitle: "1TB", target: self, action: #selector(updateModelSummary))
        check1tb.state = .off
        check1tb.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(check1tb)
        
        check2tb = NSButton(checkboxWithTitle: "2TB", target: self, action: #selector(updateModelSummary))
        check2tb.state = .off
        check2tb.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(check2tb)
        
        modelSummaryLabel = NSTextField(labelWithString: "")
        modelSummaryLabel.font = NSFont.systemFont(ofSize: 11)
        modelSummaryLabel.textColor = .secondaryLabelColor
        modelSummaryLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(modelSummaryLabel)
        
        // --- Row 4: Discord Webhook URL & Hourly Heartbeat Checkbox ---
        let phoneLabel = NSTextField(labelWithString: "📱 Discord Webhook:")
        phoneLabel.font = NSFont.boldSystemFont(ofSize: 12)
        phoneLabel.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(phoneLabel)
        
        discordField = NSTextField()
        discordField.placeholderString = "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL (Optional)"
        discordField.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(discordField)
        
        checkHourlyHeartbeat = NSButton(checkboxWithTitle: "Hourly Heartbeat (@everyone)", target: self, action: #selector(preferenceChanged))
        checkHourlyHeartbeat.state = .on
        checkHourlyHeartbeat.toolTip = "Sends an hourly status overview card to Discord (@everyone) with active checks and uptime."
        checkHourlyHeartbeat.translatesAutoresizingMaskIntoConstraints = false
        bContent.addSubview(checkHourlyHeartbeat)
        
        // 3. Status Bar
        statusLabel = NSTextField(labelWithString: "Status: ⏹ Idle")
        statusLabel.font = NSFont.boldSystemFont(ofSize: 11)
        statusLabel.textColor = .systemGreen
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(statusLabel)
        
        // 4. Log Console (Scrollable NSTextView, fully responsive)
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.autohidesScrollers = true
        scroll.borderType = .bezelBorder
        scroll.translatesAutoresizingMaskIntoConstraints = false
        
        textView = NSTextView()
        textView.isEditable = false
        textView.font = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        textView.backgroundColor = NSColor(calibratedRed: 0.12, green: 0.12, blue: 0.14, alpha: 1.0)
        textView.textColor = .white
        textView.autoresizingMask = [.width]
        textView.isHorizontallyResizable = false
        textView.isVerticallyResizable = true
        textView.textContainer?.widthTracksTextView = true
        
        scroll.documentView = textView
        content.addSubview(scroll)
        
        // --- Auto Layout Constraints ---
        NSLayoutConstraint.activate([
            // Header
            title.topAnchor.constraint(equalTo: content.topAnchor, constant: 14),
            title.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            
            sub.topAnchor.constraint(equalTo: title.bottomAnchor, constant: 3),
            sub.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            sub.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
            
            // Settings Box (Expands with window width)
            box.topAnchor.constraint(equalTo: sub.bottomAnchor, constant: 10),
            box.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            box.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
            box.heightAnchor.constraint(equalToConstant: 168),
            
            // --- Row 1 Constraints ---
            regionLabel.topAnchor.constraint(equalTo: bContent.topAnchor, constant: 8),
            regionLabel.leadingAnchor.constraint(equalTo: bContent.leadingAnchor, constant: 10),
            
            regionPopUp.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            regionPopUp.leadingAnchor.constraint(equalTo: regionLabel.trailingAnchor, constant: 6),
            regionPopUp.widthAnchor.constraint(equalToConstant: 165),
            
            browserLabel.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            browserLabel.leadingAnchor.constraint(equalTo: regionPopUp.trailingAnchor, constant: 14),
            
            browserPopUp.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            browserPopUp.leadingAnchor.constraint(equalTo: browserLabel.trailingAnchor, constant: 6),
            browserPopUp.widthAnchor.constraint(equalToConstant: 135),
            
            clearBtn.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            clearBtn.trailingAnchor.constraint(equalTo: bContent.trailingAnchor, constant: -10),
            clearBtn.widthAnchor.constraint(equalToConstant: 55),
            
            testBtn.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            testBtn.trailingAnchor.constraint(equalTo: clearBtn.leadingAnchor, constant: -6),
            testBtn.widthAnchor.constraint(equalToConstant: 65),
            
            startBtn.centerYAnchor.constraint(equalTo: regionLabel.centerYAnchor),
            startBtn.trailingAnchor.constraint(equalTo: testBtn.leadingAnchor, constant: -6),
            startBtn.widthAnchor.constraint(equalToConstant: 145),
            
            // --- Row 2 Constraints ---
            pLabel.topAnchor.constraint(equalTo: regionLabel.bottomAnchor, constant: 14),
            pLabel.leadingAnchor.constraint(equalTo: bContent.leadingAnchor, constant: 10),
            
            postcodeField.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            postcodeField.leadingAnchor.constraint(equalTo: pLabel.trailingAnchor, constant: 4),
            postcodeField.widthAnchor.constraint(equalToConstant: 85),
            postcodeField.heightAnchor.constraint(equalToConstant: 22),
            
            rLabel.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            rLabel.leadingAnchor.constraint(equalTo: postcodeField.trailingAnchor, constant: 12),
            
            radiusField.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            radiusField.leadingAnchor.constraint(equalTo: rLabel.trailingAnchor, constant: 4),
            radiusField.widthAnchor.constraint(equalToConstant: 45),
            radiusField.heightAnchor.constraint(equalToConstant: 22),
            
            miLabel.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            miLabel.leadingAnchor.constraint(equalTo: radiusField.trailingAnchor, constant: 3),
            
            iLabel.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            iLabel.leadingAnchor.constraint(equalTo: miLabel.trailingAnchor, constant: 10),
            
            intervalField.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            intervalField.leadingAnchor.constraint(equalTo: iLabel.trailingAnchor, constant: 4),
            intervalField.widthAnchor.constraint(equalToConstant: 40),
            intervalField.heightAnchor.constraint(equalToConstant: 22),
            
            sLabel.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            sLabel.leadingAnchor.constraint(equalTo: intervalField.trailingAnchor, constant: 3),
            
            colorLabel.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            colorLabel.leadingAnchor.constraint(equalTo: sLabel.trailingAnchor, constant: 14),
            
            colorPopUp.centerYAnchor.constraint(equalTo: pLabel.centerYAnchor),
            colorPopUp.leadingAnchor.constraint(equalTo: colorLabel.trailingAnchor, constant: 6),
            colorPopUp.widthAnchor.constraint(equalToConstant: 125),
            
            // --- Row 3 Constraints ---
            storageLabel.topAnchor.constraint(equalTo: pLabel.bottomAnchor, constant: 14),
            storageLabel.leadingAnchor.constraint(equalTo: bContent.leadingAnchor, constant: 10),
            
            check256.centerYAnchor.constraint(equalTo: storageLabel.centerYAnchor),
            check256.leadingAnchor.constraint(equalTo: storageLabel.trailingAnchor, constant: 6),
            
            check512.centerYAnchor.constraint(equalTo: storageLabel.centerYAnchor),
            check512.leadingAnchor.constraint(equalTo: check256.trailingAnchor, constant: 6),
            
            check1tb.centerYAnchor.constraint(equalTo: storageLabel.centerYAnchor),
            check1tb.leadingAnchor.constraint(equalTo: check512.trailingAnchor, constant: 6),
            
            check2tb.centerYAnchor.constraint(equalTo: storageLabel.centerYAnchor),
            check2tb.leadingAnchor.constraint(equalTo: check1tb.trailingAnchor, constant: 6),
            
            modelSummaryLabel.centerYAnchor.constraint(equalTo: storageLabel.centerYAnchor),
            modelSummaryLabel.leadingAnchor.constraint(equalTo: check2tb.trailingAnchor, constant: 8),
            modelSummaryLabel.trailingAnchor.constraint(lessThanOrEqualTo: bContent.trailingAnchor, constant: -10),
            
            // --- Row 4 Constraints (Discord Webhook & Heartbeat Checkbox) ---
            phoneLabel.topAnchor.constraint(equalTo: storageLabel.bottomAnchor, constant: 14),
            phoneLabel.leadingAnchor.constraint(equalTo: bContent.leadingAnchor, constant: 10),
            
            checkHourlyHeartbeat.centerYAnchor.constraint(equalTo: phoneLabel.centerYAnchor),
            checkHourlyHeartbeat.trailingAnchor.constraint(equalTo: bContent.trailingAnchor, constant: -10),
            checkHourlyHeartbeat.widthAnchor.constraint(equalToConstant: 200),
            
            discordField.centerYAnchor.constraint(equalTo: phoneLabel.centerYAnchor),
            discordField.leadingAnchor.constraint(equalTo: phoneLabel.trailingAnchor, constant: 6),
            discordField.trailingAnchor.constraint(equalTo: checkHourlyHeartbeat.leadingAnchor, constant: -8),
            discordField.heightAnchor.constraint(equalToConstant: 22),
            
            // Status Label
            statusLabel.topAnchor.constraint(equalTo: box.bottomAnchor, constant: 8),
            statusLabel.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 22),
            statusLabel.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
            
            // Log Console (Takes all remaining width AND vertical space)
            scroll.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 6),
            scroll.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            scroll.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
            scroll.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -20),
        ])
        
        loadPreferences()
        
        appendLog("🍏 Apple Stock Monitor Initialized.\nRegions: UK & US supported • Browsers: Firefox, Safari, Chrome\nStorages: 256GB, 512GB, 1TB, 2TB • Colours: Night Sky, Star White\nSelect your parameters and click 'Start Monitoring', or '🧪 Test' to verify alerts.\n\n")
        
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    
    func appendLog(_ text: String) {
        DispatchQueue.main.async {
            self.textView.textStorage?.append(NSAttributedString(
                string: text,
                attributes: [
                    .foregroundColor: NSColor.white,
                    .font: NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
                ]
            ))
            self.textView.scrollToEndOfDocument(nil)
        }
    }
    
    @objc func regionChanged() {
        let isUS = (regionPopUp.indexOfSelectedItem == 1)
        if isUS {
            pLabel.stringValue = "US ZIP:"
            if postcodeField.stringValue == "W1B 3AG" || postcodeField.stringValue.contains(" ") {
                postcodeField.stringValue = "10001"
            }
        } else {
            pLabel.stringValue = "Postcode:"
            if postcodeField.stringValue == "10001" {
                postcodeField.stringValue = "W1B 3AG"
            }
        }
        updateModelSummary()
        savePreferences()
    }
    
    @objc func preferenceChanged() {
        updateModelSummary()
        savePreferences()
    }
    
    func savePreferences() {
        let defaults = UserDefaults.standard
        defaults.set(regionPopUp.indexOfSelectedItem, forKey: "savedRegion")
        defaults.set(browserPopUp.indexOfSelectedItem, forKey: "savedBrowser")
        defaults.set(postcodeField.stringValue, forKey: "savedLocation")
        defaults.set(radiusField.stringValue, forKey: "savedRadius")
        defaults.set(intervalField.stringValue, forKey: "savedInterval")
        defaults.set(colorPopUp.indexOfSelectedItem, forKey: "savedColor")
        defaults.set(check256.state == .on, forKey: "saved256")
        defaults.set(check512.state == .on, forKey: "saved512")
        defaults.set(check1tb.state == .on, forKey: "saved1tb")
        defaults.set(check2tb.state == .on, forKey: "saved2tb")
        defaults.set(checkHourlyHeartbeat.state == .on, forKey: "savedHourlyHeartbeat")
        defaults.set(discordField.stringValue, forKey: "savedDiscord")
    }
    
    func loadPreferences() {
        let defaults = UserDefaults.standard
        if defaults.object(forKey: "savedBrowser") != nil {
            browserPopUp.selectItem(at: defaults.integer(forKey: "savedBrowser"))
        }
        if defaults.object(forKey: "savedRegion") != nil {
            regionPopUp.selectItem(at: defaults.integer(forKey: "savedRegion"))
            regionChanged()
        }
        if let loc = defaults.string(forKey: "savedLocation"), !loc.isEmpty {
            postcodeField.stringValue = loc
        }
        if let rad = defaults.string(forKey: "savedRadius"), !rad.isEmpty {
            radiusField.stringValue = rad
        }
        if let inv = defaults.string(forKey: "savedInterval"), !inv.isEmpty {
            intervalField.stringValue = inv
        }
        if defaults.object(forKey: "savedColor") != nil {
            colorPopUp.selectItem(at: defaults.integer(forKey: "savedColor"))
        }
        if defaults.object(forKey: "saved256") != nil {
            check256.state = defaults.bool(forKey: "saved256") ? .on : .off
        }
        if defaults.object(forKey: "saved512") != nil {
            check512.state = defaults.bool(forKey: "saved512") ? .on : .off
        }
        if defaults.object(forKey: "saved1tb") != nil {
            check1tb.state = defaults.bool(forKey: "saved1tb") ? .on : .off
        }
        if defaults.object(forKey: "saved2tb") != nil {
            check2tb.state = defaults.bool(forKey: "saved2tb") ? .on : .off
        }
        if defaults.object(forKey: "savedHourlyHeartbeat") != nil {
            checkHourlyHeartbeat.state = defaults.bool(forKey: "savedHourlyHeartbeat") ? .on : .off
        }
        if let disc = defaults.string(forKey: "savedDiscord"), !disc.isEmpty {
            discordField.stringValue = disc
        }
        updateModelSummary()
    }
    
    func getSelectedSKUs() -> [String] {
        let isUS = (regionPopUp.indexOfSelectedItem == 1)
        let selectedColor = colorPopUp.titleOfSelectedItem ?? "Both Colours"
        var storages: [String] = []
        if check256.state == .on { storages.append("256GB") }
        if check512.state == .on { storages.append("512GB") }
        if check1tb.state == .on { storages.append("1TB") }
        if check2tb.state == .on { storages.append("2TB") }
        
        if storages.isEmpty {
            storages = ["256GB"]
            check256.state = .on
        }
        
        let ukCatalog: [String: [String: String]] = [
            "Star White": ["256GB": "MK2D4QN/A", "512GB": "MK2F4QN/A", "1TB": "MK2H4QN/A", "2TB": "MK2K4QN/A"],
            "Night Sky":  ["256GB": "MK2E4QN/A", "512GB": "MK2G4QN/A", "1TB": "MK2J4QN/A", "2TB": "MK2L4QN/A"]
        ]
        
        let usCatalog: [String: [String: String]] = [
            "Star White": ["256GB": "MK1E4LL/A", "512GB": "MK1G4LL/A", "1TB": "MK1J4LL/A", "2TB": "MK1Q4LL/A"],
            "Night Sky":  ["256GB": "MK1F4LL/A", "512GB": "MK1H4LL/A", "1TB": "MK1L4LL/A", "2TB": "MK1R4LL/A"]
        ]
        
        let activeCatalog = isUS ? usCatalog : ukCatalog
        var skus: [String] = []
        let colors = (selectedColor == "Both Colours") ? ["Night Sky", "Star White"] : [selectedColor]
        for c in colors {
            if let storeMap = activeCatalog[c] {
                for s in storages {
                    if let sku = storeMap[s] {
                        skus.append(sku)
                    }
                }
            }
        }
        return skus
    }
    
    @objc func updateModelSummary() {
        let isUS = (regionPopUp.indexOfSelectedItem == 1)
        let skus = getSelectedSKUs()
        let count = skus.count
        let color = colorPopUp.titleOfSelectedItem ?? "Both Colours"
        var storages: [String] = []
        if check256.state == .on { storages.append("256GB") }
        if check512.state == .on { storages.append("512GB") }
        if check1tb.state == .on { storages.append("1TB") }
        if check2tb.state == .on { storages.append("2TB") }
        
        let storagesText = storages.joined(separator: ", ")
        let flag = isUS ? "🇺🇸 US" : "🇬🇧 UK"
        modelSummaryLabel.stringValue = "(\(count) models: \(storagesText) in \(color) • \(flag))"
    }
    
    func getBrowserArg() -> String {
        switch browserPopUp.indexOfSelectedItem {
        case 1:  return "safari"
        case 2:  return "chrome"
        case 3:  return "default"
        default: return "firefox"
        }
    }
    
    @objc func toggleMonitoring() {
        if process != nil {
            stopMonitoring()
        } else {
            startMonitoring()
        }
    }
    
    func startMonitoring() {
        savePreferences()
        let isUS = (regionPopUp.indexOfSelectedItem == 1)
        let country = isUS ? "us" : "uk"
        let browser = getBrowserArg()
        let pc = postcodeField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let rad = radiusField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let inv = intervalField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let discord = discordField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let hourly = (checkHourlyHeartbeat.state == .on)
        let skus = getSelectedSKUs()
        let script = resolvedScriptPath
        
        let discordDisplay = discord.isEmpty ? "Disabled" : (hourly ? "Active (Hourly Heartbeat ON)" : "Active (Alerts Only)")
        appendLog("▶ Starting stock monitor (Region: \(country.uppercased()), Location: \(pc), Radius: \(rad) mi, Cadence: \(inv)s, Browser: \(browser.capitalized), Models: \(skus.count), Discord: \(discordDisplay))...\n")
        
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        var args = [
            "-u", script,
            "--country", country,
            "--browser", browser,
            "--postcode", pc,
            "--distance", rad,
            "--interval", inv,
            "--keep-monitoring"
        ]
        if hourly {
            args.append("--hourly-ping")
        } else {
            args.append("--no-hourly-ping")
        }
        args.append("--parts")
        args.append(contentsOf: skus)
        if !discord.isEmpty {
            args.append(contentsOf: ["--discord", discord])
        }
        p.arguments = args
        
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let str = String(data: data, encoding: .utf8), !str.isEmpty {
                self?.appendLog(str)
            }
        }
        
        isManualStop = false
        p.terminationHandler = { [weak self] proc in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if !self.isManualStop && self.process != nil {
                    self.process = nil
                    self.pipe?.fileHandleForReading.readabilityHandler = nil
                    self.pipe = nil
                    self.startBtn.title = "▶ Start Monitoring"
                    self.statusLabel.stringValue = "Status: ⚠️ Stopped (Exit Code \(proc.terminationStatus))"
                    self.statusLabel.textColor = .systemRed
                    self.appendLog("⚠️ Checker process exited unexpectedly with code \(proc.terminationStatus)\n")
                    self.sendQuietDiscordLog(
                        title: "⚠️ Monitor Stopped Unexpectedly",
                        desc: "The background checker process ended (Exit code: \(proc.terminationStatus)). Click 'Start Monitoring' in the app to resume.",
                        color: 15158332
                    )
                }
            }
        }
        
        do {
            try p.run()
            self.process = p
            self.pipe = pipe
            
            sleepActivity = ProcessInfo.processInfo.beginActivity(
                options: [.idleSystemSleepDisabled, .suddenTerminationDisabled],
                reason: "Continuous Apple Stock Monitoring"
            )
            
            startBtn.title = "⏹ Stop Monitoring"
            statusLabel.stringValue = "Status: 🟢 Monitoring Active (\(country.uppercased()) • \(skus.count) models near \(pc), \(rad) mi)"
            statusLabel.textColor = .systemGreen
        } catch {
            appendLog("⚠️ Failed to launch monitor: \(error)\n")
        }
    }
    
    func stopMonitoring() {
        if let p = process {
            isManualStop = true
            p.terminate()
            process = nil
            pipe?.fileHandleForReading.readabilityHandler = nil
            pipe = nil
            
            if let act = sleepActivity {
                ProcessInfo.processInfo.endActivity(act)
                sleepActivity = nil
            }
            
            sendQuietDiscordLog(
                title: "⏹ Stock Monitor Paused",
                desc: "Monitoring was paused by user.",
                color: 15105570
            )
        }
        startBtn.title = "▶ Start Monitoring"
        statusLabel.stringValue = "Status: ⏹ Idle"
        statusLabel.textColor = .systemOrange
        appendLog("⏹ Monitoring stopped.\n\n")
    }

    func sendQuietDiscordLog(title: String, desc: String, color: Int = 15105570) {
        let discord = discordField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !discord.isEmpty && discord.hasPrefix("https://discord.com/api/webhooks/") else { return }
        
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        let escapedTitle = title.replacingOccurrences(of: "'", with: "\\'")
        let escapedDesc = desc.replacingOccurrences(of: "'", with: "\\'")
        let pyCode = "import urllib.request, json, time; url = '\(discord)'; p = {'content': 'ℹ️ **\(escapedTitle)**', 'embeds': [{'title': '🍏 \(escapedTitle)', 'description': '\(escapedDesc)', 'color': \(color), 'footer': {'text': 'Apple Stock Monitor • Status Log'}, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}]}; req = urllib.request.Request(url, data=json.dumps(p).encode('utf-8'), headers={'Content-Type': 'application/json', 'User-Agent': 'AppleStockMonitor/1.0'}); urllib.request.urlopen(req, timeout=4)"
        p.arguments = ["-c", pyCode]
        try? p.run()
    }
    
    @objc func runTest() {
        savePreferences()
        let isUS = (regionPopUp.indexOfSelectedItem == 1)
        let country = isUS ? "us" : "uk"
        let browser = getBrowserArg()
        let discord = discordField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let skus = getSelectedSKUs()
        let script = resolvedScriptPath
        appendLog("\n🧪 Running alert test for \(skus.count) selected model(s) (Region: \(country.uppercased()), Browser: \(browser.capitalized), Voice alert, desktop chime, Discord phone push)...\n")
        
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        var args = [
            "-u", script,
            "--country", country,
            "--browser", browser,
            "--test-browser",
            "--parts"
        ]
        args.append(contentsOf: skus)
        if !discord.isEmpty {
            args.append(contentsOf: ["--discord", discord])
        }
        p.arguments = args
        
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let str = String(data: data, encoding: .utf8), !str.isEmpty {
                self?.appendLog(str)
            }
        }
        
        do {
            try p.run()
        } catch {
            appendLog("⚠️ Test execution failed: \(error)\n")
        }
    }
    
    @objc func clearLogs() {
        textView.string = ""
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        savePreferences()
        stopMonitoring()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
