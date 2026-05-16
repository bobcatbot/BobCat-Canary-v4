function Select(el, options={  placeholder: '', type: '', multiple: false, maxItems: 1, clearAll: false, removeBtn: false, options: []}) {
  const selectWrapper = document.querySelector(`${el}`);
  const select = selectWrapper.querySelector('.select');
  const selectSelected = select.querySelector('.select-selected');
  const selectOptions = select.querySelector('.select-options');
  const optionsList = selectOptions.querySelectorAll('.option');
  
  let selectedOptionsList = [];
  let selectedOptionsListVals = [];
  
  // Function to get the selected options
  this.getSelectedOptions = function() {
    var selectedOptions = []
    for (let i = 0; i < selectedOptionsList.length; i++) {
      var item = selectedOptionsList[i]
      selectedOptions.push(item.id ?? item.value)
    }
    return selectedOptions;
  };
  
  // Function to update and display selected options
  function updateSelectedOptions() {
    selectSelected.innerHTML = '';
    if (options.multiple && selectedOptionsList.length > 0) {
      selectedOptionsList.forEach(function(selectedOption) {
        const chip = document.createElement('div');
        chip.classList.add('chip');
        chip.setAttribute('data-type', options.type);
        chip.textContent = selectedOption.name ?? selectedOption.value;

        if (options.removeBtn) {
          const removeOption = document.createElement('span');
          removeOption.classList.add('remove-option');
          removeOption.innerHTML = '<svg width="9" height="9" class="h-2 w-2 cursor-pointer ml-1" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M0,0 L38,38 M38,0 L0,38" stroke="currentColor" data-stroke="main" stroke-width="6" stroke-linecap="round"></path></svg>';
          removeOption.addEventListener('click', function(event) {
            event.stopPropagation();
            removeSelectedOption(selectedOption);
          });
          chip.appendChild(removeOption);
        }

        selectSelected.appendChild(chip);
      });
    } else {
      if (selectedOptionsList.length > 0) {
        selectSelected.classList.remove('placholder')
        selectSelected.classList.add('chip')
        selectSelected.textContent = selectedOptionsList[0].name ?? selectedOptionsList[0].value;
        selectSelected.setAttribute('data-type', options.type);
      } else {
        selectSelected.classList.remove('chip')
        selectSelected.classList.remove('placholder')
        selectSelected.textContent = options.placeholder || 'Select an option';
      }
    }

    // Set the 'selected' class only for the selected options in the menu
    optionsList.forEach(function(option) {
      const isSelected = selectedOptionsList.some(function (selectedOption) {
        return (selectedOption.id && selectedOption.id === option.dataset.id) ||
               (selectedOption.name && selectedOption.name === option.dataset.name) ||
               (selectedOption.value && selectedOption.value === option.dataset.value)
      });
      option.classList.toggle('selected', isSelected);
    })

    // Trigger custom event when selected options are updated
    var selectedOptions = []
    for (let i = 0; i < selectedOptionsList.length; i++) {
      var item = selectedOptionsList[i]
      selectedOptions.push(item.id ?? item.value)
    }
    
    const event = new CustomEvent('select:update', {
      detail: {
        selectedOptions: selectedOptionsList.map((option) => option.id ?? option.value),
        selectedOptionVals: selectedOptionsListVals,
      }
    });
    selectWrapper.dispatchEvent(event);
  }

  // Remove selected option
  // function removeSelectedOption(option) {
  //   const index = selectedOptionsList.indexOf(option);
  //   if (index > -1) {
  //     selectedOptionsList.splice(index, 1);
  //     selectedOptionsListVals.splice(index, 1);
  //     updateSelectedOptions();
  
  //     // Remove the 'selected' class from the corresponding option in the menu
  //     const correspondingOption = Array.from(optionsList).find(function(element) {
  //       return element.dataset.id ?? element.dataset.value === option;
  //     });
  //     if (correspondingOption) {
  //       correspondingOption.classList.remove('selected');
  //     }
  //   }
  // }
  function removeSelectedOption(option) {
    selectedOptionsList = selectedOptionsList.filter(selected => selected.id !== option.id && selected.value !== option.value);
    selectedOptionsListVals = selectedOptionsListVals.filter(val => val !== (option.id ?? option.value));
    updateSelectedOptions();
  }

  // Clear all options
  function clearAllOptions() {
    selectedOptionsList = [];
    selectedOptionsListVals = [];
    updateSelectedOptions();
  }
  
  // Set the placeholder
  selectSelected.classList.add('placholder')
  selectSelected.textContent = options.placeholder || 'Select an option';
  
  // Load default values if options parameter is not an empty array
  if (Array.isArray(options.options) && options.options.length > 0) {
    options.options.forEach(function(defaultOption) {
      const option = Array.from(optionsList).find(function(element) {
        return (element.dataset.id && element.dataset.id === defaultOption) ||
               (element.dataset.value && element.dataset.value === defaultOption)
      });
      if (option) {
        option.classList.add('selected');
        selectSelected.classList.remove('placholder')
        
        const dictItem = { name: option.textContent, id: option.dataset.id, value: option.dataset.value};
        selectedOptionsList.push(dictItem);
      }
    });
    updateSelectedOptions();
  }
  
  // Toggle the select options
  select.addEventListener('click', function() {
    // Close the select menu after selecting an option
    if (!options.multiple || options.maxItems === 1) {
      selectOptions.classList.toggle('active');
    } else {
      selectOptions.classList.add('active');
    }
  });

  // Handle option selection
  optionsList.forEach(function(item) {
    item.addEventListener('click', function(e) {
      if (!options.multiple || options.maxItems === 0) {
        selectedOptionsList = []; // Clear previously selected options for single select
        selectedOptionsListVals = []; // Clear previously selected options for single select
      }

      // Update the selectedOptionsList based on the selected options
      const optionItem = { name: item.textContent, id: item.dataset.id, value: item.dataset.value};
      if (!item.classList.contains('selected')) {
        if (options.maxItems === 0 || selectedOptionsList.length < options.maxItems) {
          selectedOptionsList.push(optionItem);
        }
      } else {
        removeSelectedOption(optionItem);
      }

      // Update and display the selected options
      updateSelectedOptions();
    });
  });

  // Add clearAll button if clearAll option is true
  if (options.clearAll) {
    const clearAllButton = document.createElement('button');
    clearAllButton.textContent = 'X';
    clearAllButton.classList.add('clear-all-button');
    clearAllButton.addEventListener('click', function(event) {
      event.stopPropagation();
      clearAllOptions();
    });
    select.appendChild(clearAllButton);
  }

  // Close the select options when clicking outside
  document.addEventListener('click', function(event) {
    if (!selectWrapper.contains(event.target)) {
      selectOptions.classList.remove('active');
    }
  });

  // Close the select options when pressing the Escape key
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      selectOptions.classList.remove('active');
    }
  });
}