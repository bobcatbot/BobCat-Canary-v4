try {
  const dropdownSelectMenusSingle = document.querySelectorAll('.dropdown-select-menu.single');
  dropdownSelectMenusSingle.forEach((dropdownSelectSingle) => {
    const dropdownSelectMenuSingle = dropdownSelectSingle.querySelector('.dropdown-select');
    const dropdownOptionsSingle = dropdownSelectSingle.querySelector('.dropdown-options');
    const selectedOptionsSingle = dropdownSelectSingle.querySelector('.selected-options');
    
    dropdownSelectSingle.addEventListener('click', () => {
      dropdownOptionsSingle.classList.toggle('show');
    });

    dropdownOptionsSingle.addEventListener('click', (event) => {
      if (event.target.tagName === 'LABEL') {
        const selected = event.target.textContent;
        selectedOptionsSingle.textContent = selected;
  
        var dropdownOptions = dropdownOptionsSingle.children
        for (let i = 0; i < dropdownOptions.length; i++) {
          dropdownOptions[i].classList.remove('selected');
        }
        event.target.classList.add('selected');
        
        dropdownSelectMenuSingle.classList.add('selected');
        dropdownSelectMenuSingle.querySelector('.placeholder').classList.add('hide');
        dropdownOptionsSingle.classList.remove('show');
      }
    });
  });
} catch (error) {
}

try {
  const dropdownSelectMenusMulti = document.querySelectorAll('.dropdown-select-menu.multi');
  dropdownSelectMenusMulti.forEach((dropdownSelectMulti) => {
    const dropdownSelectMenuMulti = dropdownSelectMulti.querySelector('.dropdown-select');
    const dropdownOptionsMulti = dropdownSelectMulti.querySelector('.dropdown-options');
    const selectedOptionsMulti = dropdownSelectMulti.querySelector('.selected-options');
    const checkboxes = document.querySelectorAll('.dropdown-options input[type="checkbox"]');
    
    dropdownSelectMulti.addEventListener('click', () => {
      dropdownOptionsMulti.classList.toggle('show');
    });

    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        const selected = [...checkboxes].filter((c) => c.checked).map((c) => c.value);
        updateSelectedOptions(selected);
      });
    });

    function updateSelectedOptions(selected) {
      selectedOptionsMulti.innerHTML = '';
      if (selected.length > 0) {
        selected.forEach((value) => {
          const option = document.createElement('div');
          option.classList.add('option');
          const label = document.createElement('span');
          label.textContent = value;
          const removeBtn = document.createElement('a');
          removeBtn.innerHTML = '&times;';
          removeBtn.addEventListener('click', () => {
            console.log(value)
            document.querySelector(`.dropdown-options input`).checked = false;
            
            const selected = [...checkboxes].filter((c) => c.checked).map((c) => c.value);
            updateSelectedOptions(selected);
          });
          option.appendChild(label);
          option.appendChild(removeBtn);
          selectedOptionsMulti.appendChild(option);
        });
        dropdownSelectMulti.classList.add('selected');
        dropdownSelectMulti.querySelector('.placeholder').classList.add('hide');
      } else {
        dropdownSelectMulti.classList.remove('selected');
        dropdownSelectMulti.querySelector('.placeholder').classList.remove('hide');
      }
    }
  });
} catch (error) {
}