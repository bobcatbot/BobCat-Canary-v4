/* Usage
EmojiPicker({
  trigger: 'button',
  position: ['bottom', 'right'],
  dir: 'directory/to/json',
  onload: () => {},
  emit(emoji) {
    console.log(emoji);
  }
});
*/

const EmojiPicker = function (options) {
  this.options = options;

  if (!this.options) {
    return console.error('You must provide object as a first argument')
  }

  this.init = () => {
    this.selectors.trigger = this.options.hasOwnProperty('trigger') ? this.options.trigger : console.error('You must proved trigger element like this - \'EmojiPicker.init({trigger: "selector"})\' ');
    this.selectors.search = '.emoji-picker-search input';
    this.selectors.emojiContainer = '.emoji-picker-grid'
    this.emojiItems = undefined;
    this.variable.plug = this.options.plug || '';
    this.variable.emit = this.options.emit || null;
    this.variable.position = this.options.position || null;
    this.variable.dir = '/static/Emojis.json';
    if (!this.selectors.trigger) return;

    this.bindEvents();
    this.variable.onload = this.options.onload || null;
  }

  this.variable = {
    position: null,
    dir: '',
    onload: null
  }

  this.selectors = {
    emit: null,
    trigger: null
  }

  this.bindEvents = () => {
    var elem = document.querySelector(this.selectors.trigger)
    
    document.body.addEventListener('click', this.functions.removeEmojiPicker.bind(this));
    elem.addEventListener('click', this.functions.emitEmoji.bind(this));
    elem.addEventListener('click', this.functions.openEmojiSelector.bind(this), this.selectors.trigger);
    elem.addEventListener('input', this.functions.search.bind(this), this.selectors.search);
  }

  this.functions = {

    // Search
    search(e) {
      const val = e.target.value;
      if (!Array.isArray(this.emojiItems)) {
        this.emojiItems = Array.from(e.target.closest('.emoji-picker').querySelectorAll('.emoji-picker-all-categories li'));
      }
      this.emojiItems.filter(emoji => {
        if (!emoji.getAttribute('data-name').match(val)) {
          emoji.style.display = 'none'

          // hide the empty category
          if (emoji.closest('ul').querySelectorAll('li').length === emoji.closest('ul').querySelectorAll('li[style="display: none;"]').length) {
            emoji.closest('.emoji-picker-category').style.display = 'none'
          }
        } else {
          emoji.style.display = ''
          emoji.closest('.emoji-picker-category').style.display = ''
        }
      })

      if (!val.length) this.emojiItems = undefined;
    },

    removeEmojiPicker(e) {
      const el = e.target;
      const picker = document.querySelector('.emoji-picker');

      if (!el.closest('.emoji-picker')) picker ? picker.remove() : false;
      this.emojiItems = undefined
    },

    emitEmoji(e) {
      const el = e.target;

      if (el.tagName.toLowerCase() == 'a' && el.className.includes('emoji-picker-item')) {
        e.preventDefault();

        let emoji_data = {
          icon: el.getAttribute('href'),
          name: el.getAttribute('name')
        }
        if (this.variable.emit)
          this.variable.emit(emoji_data, this.triggerer)

        this.functions.removeEmojiPicker(e);
      }

    },

    // Open omoji picker
    openEmojiSelector(e) {
      let el = e.target.closest(this.selectors.trigger)
      if (el) {
        e.preventDefault();

        // Bounding rect
        // Trigger position and (trigger) sizes
        if (typeof this.variable.emit === 'function') this.triggerer = el

        // Emoji Picker Promise
        this.emojiPicker().then(emojiPicker => {

          // Check if trigger has 'position: relative;' or 'position-relative' class
          if (window.getComputedStyle(el).position !== 'relative' && !el.classList.contains('position-relative')) {
            el.style.position = 'relative';
          }

          // Insert picker
          if (!document.querySelector('.emoji-picker')) {
            // onload callback
            document.querySelector(this.options.trigger).insertAdjacentHTML('beforeend', emojiPicker);
            if (typeof this.variable.onload === 'function') this.variable.onload();
          }
    
          const emojiPickerMain = document.querySelector('.emoji-picker');
          const emojiFooter = emojiPickerMain.querySelector('.emoji-picker-footer');
          const emojiBody = emojiPickerMain.querySelector('.emoji-picker-all-categories')

          // Positioning emoji container
          let positions = {
            buttonTop: el.offsetHeight,
            buttonWidth: el.offsetWidth,
            buttonFromLeft: el.getBoundingClientRect().left,
            bodyHeight: document.body.offsetHeight,
            bodyWidth: document.body.offsetWidth,
            windowScrollPosition: window.pageYOffset,
            emojiHeight: emojiPickerMain.offsetHeight,
            emojiWidth: emojiPickerMain.offsetWidth,
          }

          let position = {
            top: positions.buttonTop + 10,
            left: positions.buttonFromLeft - positions.emojiWidth,
            bottom: positions.buttonTop,
            right: positions.buttonFromLeft + positions.buttonWidth
          }

          if (this.variable.position) {
            this.variable.position.forEach(elemPos => {

              if (elemPos === 'bottom') {
                emojiPickerMain.style.top = position[elemPos] + 5 + 'px';
              }
              if (elemPos === 'top') {
                emojiPickerMain.style.bottom = position[elemPos] - 5 + 'px';
              }

              // else if (elemPos === 'right') {
              //   emojiPickerMain.style.left = position[elemPos] + 8 + 'px';
              // }
              // else {
              //   emojiPickerMain.style[elemPos] = position[elemPos] - 5 + 'px';
              // }
            })
          }
  
          // Add event listener on click
          document.querySelector('.emoji-picker').onclick = function(e) {
            e.preventDefault();
  
            let scrollTo = (element, to, duration = 100) => {
              if (duration <= 0) return;
              
              var difference = to - 65 - element.scrollTop;
              var perTick = difference / duration * 10;
  
              setTimeout(function() {
                element.scrollTop = element.scrollTop + perTick;
                if (element.scrollTop === to) return;
                scrollTo(element, to, duration - 10);
              }, 10);
            }
  
            const el = e.target;
            const filterLlnk = el.closest('a');
  
            document.querySelectorAll('.emoji-picker-categories li').forEach(item => item.classList.remove('active'))
  
            if (filterLlnk && filterLlnk.closest('li') && filterLlnk.closest('li').getAttribute('data-index')) {
              let list = filterLlnk.closest('li')
              list.classList.add('active');
              let listIndex = list.getAttribute('data-index');
              scrollTo(emojiBody, emojiBody.querySelector(`#${listIndex}`).offsetTop);
            }
  
          }
        })
      }
    },
  },
    
    // Create emoji container / Builder engine
  this.emojiPicker = () => {
    let categoryIcons = {
      'search': `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 511.999 511.999">
          <g><g> 
            <path d="M508.874,478.708L360.142,329.976c28.21-34.827,45.191-79.103,45.191-127.309c0-111.75-90.917-202.667-202.667-202.667 S0,90.917,0,202.667s90.917,202.667,202.667,202.667c48.206,0,92.482-16.982,127.309-45.191l148.732,148.732 c4.167,4.165,10.919,4.165,15.086,0l15.081-15.082C513.04,489.627,513.04,482.873,508.874,478.708z M202.667,362.667 c-88.229,0-160-71.771-160-160s71.771-160,160-160s160,71.771,160,160S290.896,362.667,202.667,362.667z"/>
          </g></g>
          <g></g><g></g><g></g><g></g>
        </svg>
      `,
      
      'people': `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20">
          <path d="M0 0h24v24H0V0z" fill="none"/>
          <circle cx="15.5" cy="9.5" r="1.5"/>
          <circle cx="8.5" cy="9.5" r="1.5"/>
          <path d="M12 16c-1.48 0-2.75-.81-3.45-2H6.88c.8 2.05 2.79 3.5 5.12 3.5s4.32-1.45 5.12-3.5h-1.67c-.69 1.19-1.97 2-3.45 2zm-.01-14C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/>
        </svg>
      `,
      'nature': `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 354.968 354.968">
          <g><g>
            <path d="M350.775,341.319c-9.6-28.4-20.8-55.2-34.4-80.8c0.4-0.4,0.8-1.2,1.6-1.6c30.8-34.8,44-83.6,20.4-131.6 c-20.4-41.6-65.6-76.4-124.8-98.8c-57.2-22-127.6-32.4-200.4-27.2c-5.6,0.4-10,5.2-9.6,10.8c0.4,2.8,1.6,5.6,4,7.2 c36.8,31.6,50,79.2,63.6,126.8c8,28,15.6,55.6,28.4,81.2c0,0.4,0.4,0.4,0.4,0.8c30.8,59.6,78,81.2,122.8,78.4 c18.4-1.2,36-6.4,52.4-14.4c9.2-4.8,18-10.4,26-16.8c11.6,23.2,22,47.2,30.4,72.8c1.6,5.2,7.6,8,12.8,6.4 C349.975,352.119,352.775,346.519,350.775,341.319z M271.175,189.319c-34.8-44.4-78-82.4-131.6-112.4c-4.8-2.8-11.2-1.2-13.6,4 c-2.8,4.8-1.2,11.2,4,13.6c50.8,28.8,92.4,64.8,125.6,107.2c13.2,17.2,25.2,35.2,36,54c-8,7.6-16.4,13.6-25.6,18 c-14,7.2-28.8,11.6-44.4,12.4c-37.6,2.4-77.2-16-104-67.6v-0.4c-11.6-24-19.2-50.8-26.8-78c-12.4-43.2-24.4-86.4-53.6-120.4 c61.6-1.6,120.4,8.4,169.2,27.2c54.4,20.8,96,52,114,88.8c18.8,38,9.2,76.8-14.4,105.2 C295.575,222.919,283.975,205.719,271.175,189.319z"/>
          </g></g>
          <g></g><g></g><g></g>
        </svg>
      `,
      'food': `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20">
          <g> <rect fill="none" width="20" y="0"/> </g>
          <g><g>
            <path d="M20.5,10.94c0.13-0.32,0.1-0.23,0.15-0.39c0.3-1.21-0.34-2.47-1.5-2.93l-2.01-0.8c-0.46-0.18-0.95-0.21-1.41-0.12 c-0.11-0.33-0.29-0.63-0.52-0.89C14.73,5.29,14.06,5,13.36,5h-2.71C9.94,5,9.27,5.29,8.8,5.81C8.56,6.07,8.38,6.37,8.27,6.69 C7.81,6.6,7.32,6.63,6.86,6.81l-2.01,0.8c-1.16,0.46-1.8,1.72-1.5,2.93l0.15,0.38C1.1,15.55,1,15.55,1,16.38 c0,0.91,0.46,1.74,1.24,2.22c1.42,0.88,2.49,0.14,4-0.61h11.53c1.52,0.76,1.86,1.01,2.63,1.01c1,0,2.61-0.77,2.61-2.61 C23,15.54,22.88,15.51,20.5,10.94z M20.12,16.93l-1.68-0.84l1.08-2.7l1.41,2.71C21.21,16.63,20.64,17.19,20.12,16.93z M15.09,15.99l0.62-6.9c0.03-0.33,0.37-0.54,0.68-0.42l2.01,0.8c0.22,0.09,0.34,0.31,0.31,0.54l-2.4,5.98H15.09z M7.68,15.99 l-2.4-5.98C5.25,9.78,5.37,9.56,5.59,9.47l2.01-0.8c0.31-0.12,0.65,0.08,0.68,0.42l0.62,6.9H7.68z M3.07,16.1l1.41-2.72l1.08,2.71 l-1.68,0.84C3.36,17.19,2.79,16.63,3.07,16.1z M10.15,7.54c-0.03-0.31,0.23-0.54,0.5-0.54h2.71c0.27,0,0.53,0.23,0.5,0.54 l-0.77,8.45h-2.17L10.15,7.54z"/>
          </g></g>
        </svg>
      `,
      'travel': `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
          <g><g>
          <path d="M846.5,153.5C939,246.1,990,369.1,990,500c0,130.9-51,253.9-143.5,346.5C753.9,939,630.9,990,500,990c-130.9,0-253.9-51-346.5-143.5C61,753.9,10,630.9,10,500c0-130.9,51-253.9,143.5-346.5C246.1,61,369.1,10,500,10C630.9,10,753.9,61,846.5,153.5z M803.2,803.2c60.3-60.3,100.5-135.5,117-217.3c-12.9,19-25.2,26-32.9-16.5c-7.9-69.3-71.5-25-111.5-49.6c-42.1,28.4-136.8-55.2-120.7,39.1c24.8,42.5,134-56.9,79.6,33.1c-34.7,62.8-126.9,201.9-114.9,274c1.5,105-107.3,21.9-144.8-12.9c-25.2-69.8-8.6-191.8-74.6-225.9c-71.6-3.1-133-9.6-160.8-89.6c-16.7-57.3,17.8-142.5,79.1-155.7c89.8-56.4,121.9,66.1,206.1,68.4c26.2-27.4,97.4-36.1,103.4-66.8c-55.3-9.8,70.1-46.5-5.3-67.4c-41.6,4.9-68.4,43.1-46.3,75.6C496,410.3,493.5,274.8,416,317.6c-2,67.6-126.5,21.9-43.1,8.2c28.7-12.5-46.8-48.8-6-42.2c20-1.1,87.4-24.7,69.2-40.6c37.5-23.3,69.1,55.8,105.8-1.8c26.5-44.3-11.1-52.5-44.4-30c-18.7-21,33.1-66.3,78.8-85.9c15.2-6.5,29.8-10.1,40.9-9.1c23,26.6,65.6,31.2,67.8-3.2c-57-27.3-119.9-41.7-185-41.7c-93.4,0-182.3,29.7-255.8,84.6c19.8,9.1,31,20.3,11.9,34.7c-14.8,44.1-74.8,103.2-127.5,94.9c-27.4,47.2-45.4,99.2-53.1,153.6c44.1,14.6,54.3,43.5,44.8,53.2c-22.5,19.6-36.3,47.4-43.4,77.8C91.3,658,132.6,739,196.8,803.2c81,81,188.6,125.6,303.2,125.6C614.5,928.8,722.2,884.2,803.2,803.2z"/>
          </g><g>
          </g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g></g>
        </svg>
      `,
      'activity': `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 480">
          <path d="m240 0c-132.546875 0-240 107.453125-240 240s107.453125 240 240 240 240-107.453125 240-240c-.148438-132.484375-107.515625-239.851562-240-240zm8.566406 69.191406 83.433594-33.351562c9.46875 4.285156 18.628906 9.222656 27.414062 14.777344l.21875.136718c8.632813 5.46875 16.882813 11.519532 24.695313 18.109375l.671875.585938c3.503906 2.984375 6.910156 6.074219 10.222656 9.261719.417969.410156.855469.800781 1.273438 1.21875 3.472656 3.390624 6.835937 6.886718 10.089844 10.484374.269531.304688.527343.625.796874.929688 2.855469 3.199219 5.601563 6.511719 8.265626 9.878906.640624.800782 1.28125 1.601563 1.902343 2.402344 2.890625 3.742188 5.6875 7.550781 8.328125 11.480469l-16.632812 70.703125-81.832032 27.28125-78.828124-63.074219zm-186.125 34.480469c.621094-.800781 1.253906-1.601563 1.894532-2.398437 2.632812-3.339844 5.355468-6.597657 8.167968-9.777344.304688-.335938.585938-.679688.886719-1.015625 3.234375-3.605469 6.582031-7.097657 10.050781-10.480469.398438-.390625.796875-.800781 1.214844-1.160156 3.285156-3.167969 6.664062-6.238282 10.136719-9.207032l.800781-.671874c7.742188-6.542969 15.914062-12.554688 24.460938-18l.3125-.199219c8.734374-5.542969 17.835937-10.472657 27.25-14.761719l83.816406 33.191406v80.800782l-78.832032 63.0625-81.832031-27.230469-16.632812-70.703125c2.664062-3.921875 5.429687-7.722656 8.304687-11.449219zm-9.640625 259.089844c-2.351562-3.585938-4.601562-7.238281-6.746093-10.960938l-.519532-.898437c-2.132812-3.703125-4.152344-7.46875-6.054687-11.292969l-.066407-.121094c-4.007812-8.046875-7.527343-16.328125-10.535156-24.800781v-.078125c-1.421875-4-2.71875-8.097656-3.917968-12.21875l-.433594-1.519531c-1.097656-3.871094-2.09375-7.785156-2.984375-11.742188-.078125-.386718-.175781-.753906-.253907-1.136718-1.964843-8.9375-3.375-17.984376-4.226562-27.097657l48.839844-58.605469 81.265625 27.085938 23.585937 94.335938-38.753906 51.5625zm240.472657 94.78125c-4 .992187-8.105469 1.847656-12.210938 2.617187-.574219.113282-1.160156.207032-1.734375.3125-3.496094.625-7.03125 1.160156-10.574219 1.597656-.945312.121094-1.882812.25-2.824218.363282-3.289063.382812-6.609376.671875-9.9375.910156-1.046876.070312-2.082032.175781-3.128907.242188-4.253906.261718-8.542969.414062-12.863281.414062-3.957031 0-7.890625-.105469-11.800781-.3125-.472657 0-.925781-.078125-1.398438-.113281-3.480469-.199219-6.945312-.460938-10.402343-.796875l-.398438-.074219c-7.574219-.820313-15.105469-2.023437-22.558594-3.597656l-47.320312-74.089844 38.144531-50.863281h111.46875l38.769531 51.199218zm165.496093-169.542969c-.082031.382812-.175781.753906-.257812 1.136719-.894531 3.953125-1.890625 7.867187-2.984375 11.742187l-.429688 1.519532c-1.203125 4.121093-2.496094 8.203124-3.921875 12.21875v.078124c-3.007812 8.472657-6.523437 16.753907-10.535156 24.800782l-.066406.121094c-1.914063 3.828124-3.929688 7.59375-6.054688 11.292968l-.519531.898438c-2.132812 3.734375-4.378906 7.378906-6.734375 10.945312l-78.929687 12.445313-39.023438-51.519531 23.574219-94.3125 81.265625-27.085938 48.839844 58.605469c-.847657 9.117187-2.257813 18.171875-4.222657 27.113281zm0 0"/>
        </svg>
      `,
      'objects':  `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
          <g><g>
            <path d="M256,0C161.33,0,84.312,77.018,84.312,171.688c0,54.38,25.587,105.127,68.882,137.502c0,7.915,0,121.305,0,125.043 c0,9.22,7.475,16.696,16.696,16.696h10.168C187.72,485.81,218.85,512,256,512c37.15,0,68.28-26.19,75.943-61.072h10.168 c9.22,0,16.696-7.475,16.696-16.696c0-3.762,0-117.209,0-125.043c43.294-32.375,68.882-83.122,68.882-137.502 C427.688,77.018,350.67,0,256,0z M256,478.609c-18.567,0-34.507-11.461-41.116-27.68h82.233 C290.507,467.148,274.567,478.609,256,478.609z M325.415,417.537c-4.855,0-132.083,0-138.83,0v-39.041h138.83V417.537z M211.096,242.095h-8.057c-4.443,0-8.058-3.615-8.058-8.058s3.615-8.057,8.058-8.057c4.443,0,8.057,3.614,8.057,8.057V242.095z M244.488,345.105v-69.619h23.017v69.619H244.488z M332.824,286.684c-4.63,3.099-7.41,8.303-7.41,13.875v44.545h-24.519v-69.619 h8.058c22.855,0,41.449-18.594,41.449-41.45c0-22.855-18.593-41.449-41.449-41.449c-22.855,0-41.45,18.593-41.45,41.449v8.058 h-23.017v-8.058c0-22.855-18.593-41.449-41.449-41.449c-22.855,0-41.45,18.593-41.45,41.449s18.594,41.45,41.45,41.45h8.057 v69.619h-24.511V300.56c0-5.572-2.779-10.776-7.41-13.875c-38.491-25.759-61.472-68.748-61.472-114.996 c0-76.258,62.039-138.297,138.297-138.297S394.297,95.43,394.297,171.688C394.297,217.937,371.316,260.926,332.824,286.684z M300.896,242.095v-8.058c0-4.443,3.615-8.057,8.058-8.057c4.443,0,8.057,3.614,8.057,8.057s-3.614,8.058-8.057,8.058H300.896z"/>
          </g></g>
          <g></g><g></g><g></g><g></g><g></g><g></g>
        </svg>
      `,
      'symbols': `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20">
          <g><rect fill="none" height="24" width="24"/></g>
          <g>
            <rect height="2" width="8" x="3" y="2"/>
            <polygon points="6,11 8,11 8,7 11,7 11,5 3,5 3,7 6,7"/>
            <rect height="2" transform="matrix(0.7071 -0.7071 0.7071 0.7071 -7.0416 16.9999)" width="11" x="11.5" y="16"/>
            <circle cx="14.5" cy="14.5" r="1.5"/>
            <circle cx="19.5" cy="19.5" r="1.5"/>
            <path d="M15.5,11c1.38,0,2.5-1.12,2.5-2.5V4h3V2h-4v4.51C16.58,6.19,16.07,6,15.5,6C14.12,6,13,7.12,13,8.5 C13,9.88,14.12,11,15.5,11z"/><path d="M9.74,15.96l-1.41,1.41l-0.71-0.71l0.35-0.35c0.98-0.98,0.98-2.56,0-3.54c-0.49-0.49-1.13-0.73-1.77-0.73 c-0.64,0-1.28,0.24-1.77,0.73c-0.98,0.98-0.98,2.56,0,3.54l0.35,0.35l-1.06,1.06c-0.98,0.98-0.98,2.56,0,3.54 C4.22,21.76,4.86,22,5.5,22s1.28-0.24,1.77-0.73l1.06-1.06l1.41,1.41l1.41-1.41l-1.41-1.41l1.41-1.41L9.74,15.96z M5.85,14.2 c0.12-0.12,0.26-0.15,0.35-0.15s0.23,0.03,0.35,0.15c0.19,0.2,0.19,0.51,0,0.71l-0.35,0.35L5.85,14.9 C5.66,14.71,5.66,14.39,5.85,14.2z M5.85,19.85C5.73,19.97,5.59,20,5.5,20s-0.23-0.03-0.35-0.15c-0.19-0.19-0.19-0.51,0-0.71 l1.06-1.06l0.71,0.71L5.85,19.85z"/>
          </g>
        </svg>
      `,
      'flags': `
        <svg width="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
          <g><g>
            <path id="Shape" d="m59.0752 28.5054c-3.7664123-1.873859-7.2507049-4.2678838-10.3506-7.1118 1.5923634-6.0211307 2.7737841-12.14349669 3.5361-18.3248.1788-1.44-.623-1.9047-.872-2.0126-.7016942-.26712004-1.4944908-.00419148-1.8975.6293-5.4726 6.5479-12.9687 5.8008-20.9053 5.0054-7.9985-.8-16.2506-1.6116-22.3684 5.4114-.85552122-1.067885-2.26533581-1.5228479-3.5837-1.1565l-.1377.0386c-1.81412367.5095218-2.87378593 2.391025-2.3691 4.2065l12.2089 43.6891c.3541969 1.2645215 1.5052141 2.1399137 2.8184 2.1435.2677318-.0003961.5341685-.0371657.792-.1093l1.0683-.2984h.001c.7485787-.2091577 1.3833789-.7071796 1.7646969-1.3844635.381318-.677284.4779045-1.478326.2685031-2.2268365l-3.7812-13.5327c5.5066-7.0807 13.18-6.3309 21.2988-5.52 8.1094.81 16.4863 1.646 22.64-5.7129l.0029-.0039c.6044387-.7534187.8533533-1.7315007.6826-2.6822-.0899994-.4592259-.3932698-.8481635-.8167-1.0474zm-42.0381 29.7446c-.1201754.2157725-.3219209.3742868-.56.44l-1.0684.2983c-.4949157.1376357-1.0078362-.1513714-1.1465-.646l-12.2095-43.6895c-.20840349-.7523825.23089143-1.5316224.9825-1.7428l.1367-.0381c.12366014-.0348192.25153137-.0524183.38-.0523.63429117.0010181 1.19083557.4229483 1.3631 1.0334l.1083.3876v.0021l6.2529 22.3755 5.8468 20.9238c.0669515.2380103.0360256.4929057-.0859.708zm40.6329-27.2925c-5.4736 6.5459-12.9707 5.7974-20.9043 5.0039-7.9033-.79-16.06-1.605-22.1552 5.1558l-5.463-19.548-2.0643-7.3873c5.5068-7.0794 13.1796-6.3119 21.3045-5.5007 7.7148.7695 15.6787 1.5664 21.7373-4.7095-.7467138 5.70010904-1.859683 11.3462228-3.332 16.9033-.1993066.7185155.0267229 1.4878686.583 1.9844 3.1786296 2.9100325 6.7366511 5.3762694 10.5771 7.3315-.0213812.2768572-.1194065.5422977-.2831.7666z"/>
          </g></g>
        </svg>
      `,
    }
  
    //${categoryIcons.search}
    let picker = `
      <div class="emoji-picker ${this.options.plug}">
          <div class="emoji-picker-categories">%categories%</div>
          <div>
            <div class="emoji-picker-search">
              <input placeholder="Search emoji" />
            </div>
            %pickerContainer%
          </div>
      </div>`;
  
    let categories = '<ul>%categories%</ul>';
    let categoriesInner = ``;
    let outerUl = `<div class="emoji-picker-all-categories">%outerUL%</div>`;
    let innerLists = ``;
  
    let index = 0; // Index count
  
    const fetchData = fetch(`${this.variable.dir}`)
      .then(response => response.json())
      .then(emojis => {
        for (const key in emojis) {
          if (emojis.hasOwnProperty(key)) {
            index += 1; // Index count
  
            let keyToId = key.split(' ').join('-').split('&').join('').toLowerCase();
  
            const categories = emojis[key];
            
            categoriesInner += `<li class="${index === 1 ? 'active' : ''}" id="${keyToId}" data-index="${keyToId}"><a href="#${keyToId}">${categoryIcons[keyToId]}</a></li>`
  
            innerLists += `
              <ul class="emoji-picker-category ${index === 1 ? 'active' : ''}" id="${keyToId}" category-name="${key}">
                <div class="emoji-picker-container-title"><div style="margin-right:5px">${categoryIcons[keyToId]}</div> ${key}</div>
                  <div class="emoji-picker-grid">
            `;
  
            // Loop through emoji items
            categories.forEach(item => {
              innerLists += `
                <li data-name="${item.name}">
                  <a class="emoji-picker-item" href="${item.emoji}" title="${item.name}" data-name="${item.name}" data-code="${item.code}">
                    ${item.emoji}
                  </a>
                </li>
              `;
            })
  
            innerLists += `
                </div>
              </ul>
            `;
          }
        }
        
        let allSmiles = outerUl.replace('%outerUL%', innerLists)
        let cats = categories.replace('%categories%', categoriesInner);
        let pickerContainer = picker.replace('%pickerContainer%', allSmiles)
        let data = pickerContainer.replace('%categories%', cats);
        return data;
      })
  
    return fetchData;
  }
  
  this.init()
}