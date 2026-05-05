/* Auto-submit + reset bindings for the leads filter form. */
(function () {
  const form = document.getElementById('filterForm');
  if (!form) return;

  // Submit on select change (skip score_min — keep that explicit)
  form.querySelectorAll('select').forEach(el => {
    el.addEventListener('change', () => form.submit());
  });

  // Reset button
  const reset = document.getElementById('resetFilters');
  if (reset) {
    reset.addEventListener('click', e => {
      e.preventDefault();
      window.location = form.action || window.location.pathname;
    });
  }
})();
