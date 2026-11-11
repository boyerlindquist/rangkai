document.addEventListener('DOMContentLoaded', function () {
  const driver = window.driver.js.driver;
  
  const tourSteps = [
    // --- DASHBOARD ( / or /dashboard/ ) ---
    { route: '/', element: '#guide-overview', popover: { title: 'Dashboard', description: 'Pusat kendali persiapan pernikahan Anda. Cek semuanya secara sekilas.' } },
    { route: '/', element: '#guide-dday', popover: { title: 'D-Day Countdown', description: 'Hitung mundur menuju hari bahagia Anda berdasarkan tanggal yang diset di Pengaturan.' } },
    { route: '/', element: '#guide-budget-rem', popover: { title: 'Sisa Budget', description: 'Total budget dikurangi dengan pembayaran aktual (paid).' } },
    { route: '/', element: '#guide-rsvp', popover: { title: 'RSVP Hadir', description: 'Jumlah tamu dan pax yang telah mengonfirmasi kehadiran (Attending).' } },
    { route: '/', element: '#guide-task-prog', popover: { title: 'Progress Tugas', description: 'Persentase tugas yang sudah selesai dari total keseluruhan.' } },
    { route: '/', element: '#guide-attention', popover: { title: 'Perlu Perhatian', description: 'Notifikasi kritis yang harus segera ditindaklanjuti.' } },
    { route: '/', element: '#guide-active-tasks', popover: { title: 'Tugas Aktif', description: 'Daftar tugas timeline yang sedang berjalan.' } },
    { route: '/', element: '#guide-quick-actions', popover: { title: 'Aksi Cepat', description: 'Pintasan instan ke menu-menu krusial.' } },
    
    // --- BUDGET & FINANCE ( /budgets/ ) ---
    { route: '/budgets/', element: '#guide-budget', popover: { title: 'Budget & Finance', description: 'Kelola seluruh alokasi dana dan pencatatan transaksi aktual.' } },
    { route: '/budgets/', element: '#guide-categories', popover: { title: 'Alokasi Kategori', description: 'Bagi budget Anda ke persentase per kategori.' } },
    { route: '/budgets/', element: '#guide-budget-summary', popover: { title: 'Ringkasan Budget', description: 'Lihat selisih (variance) antara alokasi dan pengeluaran aktual.' } },
    { route: '/budgets/', element: '#guide-split-bill', popover: { title: 'Split Bill Breakdown', description: 'Lihat porsi tagihan untuk pihak Pria, Wanita, dan Keluarga secara otomatis.' } },
    
    // --- TABUNGAN ( /budgets/savings/ ) ---
    { route: '/budgets/savings/', element: '#guide-savings', popover: { title: 'Tabungan Bersama', description: 'Pantau dana yang berhasil dikumpulkan bersama pasangan.' } },
    { route: '/budgets/savings/', element: '#guide-savings-target', popover: { title: 'Pengaturan Target', description: 'Tentukan target total tabungan dan kesanggupan setoran per bulan.' } },
    { route: '/budgets/savings/', element: '#guide-savings-progress', popover: { title: 'Progres Tabungan', description: 'Lihat estimasi berapa bulan lagi tabungan akan mencapai target.' } },
    { route: '/budgets/savings/', element: '#guide-savings-chart', popover: { title: 'Grafik Akumulasi', description: 'Pantau kurva akumulasi tabungan per penyetor dan garis target horizontal.' } },
    
    // --- GUESTS ( /guests/ ) ---
    { route: '/guests/', element: '#guide-guests', popover: { title: 'Guest List', description: 'Manajemen tamu undangan dan perhitungan catering otomatis.' } },
    { route: '/guests/', element: '#guide-catering', popover: { title: 'Catering Simulator', description: 'Otomatis hitung porsi prasmanan vs gubukan berdasar persentase kehadiran.' } },
    { route: '/guests/', element: '#guide-guest-quota', popover: { title: 'Kuota 4-Arah', description: 'Visualisasi porsi kuota undangan Keluarga vs Teman.' } },
    { route: '/guests/', element: '#guide-guest-db', popover: { title: 'Database Tamu', description: 'Catat detail kontak, RSVP, dan status kehadiran saat hari H.' } },
  
    // --- VENDORS ( /vendors/ ) ---
    { route: '/vendors/', element: '#guide-vendors', popover: { title: 'Vendor Compare', description: 'Evaluasi vendor secara objektif dengan sistem skoring.' } },
    { route: '/vendors/', element: '#guide-vendor-weights', popover: { title: 'Bobot Prioritas', description: 'Tentukan aspek apa (Harga, Kualitas, dll) yang paling penting buat Anda.' } },
    { route: '/vendors/', element: '#guide-vendor-cards', popover: { title: 'Kandidat Vendor', description: 'Bandingkan Weighted Score tiap vendor untuk mendapatkan rekomendasi paling rasional.' } },
  
    // --- OPERATIONS HUB ( /operations/ ) ---
    { route: '/operations/', element: '#guide-operations', popover: { title: 'Operations Hub', description: 'Pusat logistik dan koordinasi acara hari H.' } },
    { route: '/operations/', element: '#guide-rundown', popover: { title: 'Rundown Sanity', description: 'Peringatan otomatis jika jadwal rundown bentrok atau terlalu padat.' } },
    { route: '/operations/', element: '#guide-assets', popover: { title: 'Aset Kritis', description: 'Lacak cincin nikah, mahar, dan dokumen penting lainnya jangan sampai tertinggal.' } },
    { route: '/operations/', element: '#guide-attire', popover: { title: 'Kalkulator Kain', description: 'Hitung kebutuhan panjang kain seragam untuk rombongan keluarga.' } },
    
    // --- CHECKLIST ( /checklist/details/ ) ---
    { route: '/checklist/details/', element: '#guide-checklists', popover: { title: 'Detail Kelengkapan', description: 'Daftar periksa untuk dokumen KUA, catatan hantaran, dan seserahan.' } }
  ];

  // Helper to normalize path (handle / vs /dashboard/)
  function normalizePath(path) {
    if (path === '/dashboard/') return '/';
    return path;
  }

  const currentPath = normalizePath(window.location.pathname);
  
  // Check if a tour is active
  const isTourActive = localStorage.getItem('tour_active') === 'true';
  let currentStepIndex = parseInt(localStorage.getItem('tour_step') || '0', 10);

  // If tour is active, we should filter steps starting from current index
  if (isTourActive) {
    // If the expected route doesn't match current route, there was an anomaly. Just stop.
    if (currentStepIndex < tourSteps.length && normalizePath(tourSteps[currentStepIndex].route) !== currentPath) {
      // Find the first step on this page instead
      const firstStepOnPage = tourSteps.findIndex(s => normalizePath(s.route) === currentPath);
      if (firstStepOnPage !== -1) {
        currentStepIndex = firstStepOnPage;
      } else {
        localStorage.removeItem('tour_active');
        localStorage.removeItem('tour_step');
        return; // End tour completely
      }
    }

    // Collect steps for the current page starting from currentStepIndex
    const stepsOnThisPage = [];
    let i = currentStepIndex;
    while (i < tourSteps.length && normalizePath(tourSteps[i].route) === currentPath) {
      stepsOnThisPage.push({
        element: tourSteps[i].element,
        popover: {
          ...tourSteps[i].popover,
          side: "bottom",
          align: "start"
        }
      });
      i++;
    }

    const nextGlobalIndex = i; // The index of the first step on the NEXT page

    if (stepsOnThisPage.length > 0) {
      setTimeout(() => {
        const driverObj = driver({
          showProgress: true,
          allowClose: true,
          nextBtnText: 'Lanjut →',
          prevBtnText: '← Kembali',
          doneBtnText: 'Selesai',
          steps: stepsOnThisPage,
          onPopoverRender: (popover, { config, state }) => {
            const footer = popover.wrapper.querySelector('.driver-popover-footer');
            if (footer && !footer.querySelector('.custom-tour-btns')) {
              const btnContainer = document.createElement('div');
              btnContainer.className = 'custom-tour-btns';
              btnContainer.style.cssText = 'display: flex; gap: 8px; margin-right: auto;';

              const endBtn = document.createElement('button');
              endBtn.innerHTML = 'End Tour';
              endBtn.style.cssText = 'background: #fee2e2; border: 1px solid #fca5a5; color: #dc2626; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500;';
              endBtn.onclick = () => {
                if(confirm("Yakin ingin mengakhiri tur interaktif?")) {
                  localStorage.removeItem('tour_active');
                  localStorage.removeItem('tour_step');
                  driverObj.destroy();
                }
              };

              const skipBtn = document.createElement('button');
              skipBtn.innerHTML = 'Skip Page';
              skipBtn.style.cssText = 'background: transparent; border: 1px solid #d1d5db; color: #6b7280; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500;';
              skipBtn.onclick = () => {
                if (nextGlobalIndex < tourSteps.length) {
                  localStorage.setItem('tour_step', nextGlobalIndex.toString());
                  window.location.href = tourSteps[nextGlobalIndex].route;
                } else {
                  localStorage.removeItem('tour_active');
                  localStorage.removeItem('tour_step');
                  driverObj.destroy();
                }
              };

              btnContainer.appendChild(endBtn);
              btnContainer.appendChild(skipBtn);
              footer.insertBefore(btnContainer, footer.firstChild);
            }
          },
          onNextClick: (elem, step, { config, state }) => {
            if (state.activeIndex === stepsOnThisPage.length - 1) {
              // We reached the end of this page's tour
              if (nextGlobalIndex < tourSteps.length) {
                // There are more pages!
                localStorage.setItem('tour_step', nextGlobalIndex.toString());
                window.location.href = tourSteps[nextGlobalIndex].route; // Navigate
              } else {
                // Tour completely finished
                localStorage.removeItem('tour_active');
                localStorage.removeItem('tour_step');
                driverObj.destroy();
                
                // Show completion
                setTimeout(() => {
                  alert("🎉 Selamat! Anda telah menyelesaikan tur interaktif. Anda siap merencanakan pernikahan!");
                }, 500);
              }
            } else {
              driverObj.moveNext();
            }
          },
          onDestroyStarted: () => {
            if (driverObj.hasNextStep() || nextGlobalIndex < tourSteps.length) {
              // They closed it early
              if(confirm("Yakin ingin mengakhiri tur interaktif?")) {
                localStorage.removeItem('tour_active');
                localStorage.removeItem('tour_step');
                driverObj.destroy();
              }
            } else {
              driverObj.destroy();
            }
          }
        });
        driverObj.drive();
      }, 500); // Wait a bit for page animations
    } else if (nextGlobalIndex < tourSteps.length) {
      // Current page has no steps, but there are more pages. Jump!
      localStorage.setItem('tour_step', nextGlobalIndex.toString());
      window.location.href = tourSteps[nextGlobalIndex].route;
    }
  }

  // Global Start Function for the Guide page
  window.startComprehensiveTour = function() {
    localStorage.setItem('tour_active', 'true');
    localStorage.setItem('tour_step', '0');
    window.location.href = '/'; // Always start at dashboard
  };
});

// Helper for specific feature tooltips on hover
window.showFeatureGuide = function(elementSelector, title, description) {
  // If a main tour is running, don't trigger mini tours
  if (localStorage.getItem('tour_active') === 'true') return;

  const driver = window.driver.js.driver;
  const miniTour = driver({
    showProgress: false,
    allowClose: true,
    steps: [
      {
        element: elementSelector,
        popover: {
          title: title,
          description: description,
          side: "bottom",
          align: "start"
        }
      }
    ]
  });
  miniTour.drive();
};
