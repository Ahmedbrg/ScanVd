// frontend logic
var api_base_url = 'http://localhost:8000';

// get elements from the page
var upload_zone = document.getElementById('upload-zone');
var my_file_input = document.getElementById('file-input');
var the_progress_container = document.getElementById('progress-container');
var the_file_name_span = document.getElementById('file-name');
var progress_status_text = document.getElementById('progress-status');
var the_progress_fill_bar = document.getElementById('progress-fill');
var step1 = document.getElementById('step-upload');
var step2 = document.getElementById('step-transcribe');
var step3 = document.getElementById('step-ready');

var section_for_upload = document.getElementById('upload-section');
var section_for_search = document.getElementById('search-section');
var video_player_element = document.getElementById('video-player');
var the_search_input = document.getElementById('search-input');
var the_search_button = document.getElementById('search-btn');

var div_objects = document.getElementById('objects-container');
var list_objects = document.getElementById('objects-list');

var the_transcript_btn = document.getElementById('transcript-btn');
var the_transcript_div = document.getElementById('transcript-content');
var the_transcript_text_area = document.getElementById('transcript-text');

var div_results = document.getElementById('results-container');
var title_results = document.getElementById('results-title');
var count_results = document.getElementById('results-count');
var list_results = document.getElementById('results-list');
var div_no_results = document.getElementById('no-results');

var btn_new_video = document.getElementById('new-video-btn');
var my_toast = document.getElementById('toast');
var my_toast_msg = document.getElementById('toast-message');

// variables to store stuff
var current_video_id_string = null;
var my_transcription_data = null;

// show toast function
function showToast(msg, type) {
    if (type == undefined) {
        type = 'info';
    }
    my_toast_msg.textContent = msg;
    my_toast.className = "toast " + type;
    
    setTimeout(function() {
        my_toast.classList.add('visible');
    }, 10);
    
    setTimeout(function() {
        my_toast.classList.remove('visible');
        setTimeout(function() {
            my_toast.classList.add('hidden');
        }, 300);
    }, 4000);
}

// upload events
upload_zone.addEventListener('click', function() {
    my_file_input.click();
});

upload_zone.addEventListener('dragover', function(event) {
    event.preventDefault();
    upload_zone.classList.add('drag-over');
});

upload_zone.addEventListener('dragleave', function(event) {
    event.preventDefault();
    upload_zone.classList.remove('drag-over');
});

upload_zone.addEventListener('drop', function(event) {
    event.preventDefault();
    upload_zone.classList.remove('drag-over');
    var files_array = event.dataTransfer.files;
    if (files_array.length > 0) {
        handleFile(files_array[0]);
    }
});

my_file_input.addEventListener('change', function(event) {
    if (event.target.files.length > 0) {
        handleFile(event.target.files[0]);
    }
});

// upload file function
function handleFile(my_file) {
    // check if it is a video
    var is_video = false;
    if (my_file.type.indexOf('video/') === 0) {
        is_video = true;
    }
    
    if (is_video == false) {
        showToast('Please select a video file', 'error');
        return;
    }

    var max_size = 500 * 1024 * 1024;
    if (my_file.size > max_size) {
        showToast('File size must be under 500MB', 'error');
        return;
    }

    // hide upload zone
    upload_zone.style.display = 'none';
    the_progress_container.classList.remove('hidden');
    the_file_name_span.textContent = my_file.name;
    progress_status_text.textContent = 'Uploading...';
    the_progress_fill_bar.style.width = '0%';

    step1.className = 'progress-step active';
    step2.className = 'progress-step';
    step3.className = 'progress-step';

    // fake progress
    var progress_timer = setInterval(function() {
        var width_str = the_progress_fill_bar.style.width;
        var width_num = parseFloat(width_str);
        if (isNaN(width_num)) { width_num = 0; }
        
        if (width_num < 40) {
            the_progress_fill_bar.style.width = (width_num + 2) + '%';
        }
    }, 100);

    var form_data = new FormData();
    form_data.append('file', my_file);

    setTimeout(function() {
        clearInterval(progress_timer);
        the_progress_fill_bar.style.width = '45%';
        progress_status_text.textContent = 'Analyzing audio & objects...';
        step1.className = 'progress-step done';
        step2.className = 'progress-step active';

        var timer2 = setInterval(function() {
            var w_str = the_progress_fill_bar.style.width;
            var w_num = parseFloat(w_str);
            if (isNaN(w_num)) { w_num = 0; }
            if (w_num < 85) {
                the_progress_fill_bar.style.width = (w_num + 0.5) + '%';
            }
        }, 500);
        window.my_global_timer = timer2;
    }, 1500);

    // do the fetch
    fetch(api_base_url + '/api/upload', {
        method: 'POST',
        body: form_data
    }).then(function(response) {
        if (window.my_global_timer != null) {
            clearInterval(window.my_global_timer);
        }
        
        if (response.ok == false) {
            response.json().then(function(err_data) {
                console.error('Upload error:', err_data);
                var msg = "Upload failed";
                if (err_data.detail != null) {
                    msg = err_data.detail;
                }
                showToast(msg, 'error');
                the_progress_container.classList.add('hidden');
                upload_zone.style.display = '';
            });
        } else {
            response.json().then(function(data) {
                current_video_id_string = data.video_id;

                the_progress_fill_bar.style.width = '100%';
                progress_status_text.textContent = 'Ready!';
                step2.className = 'progress-step done';
                step3.className = 'progress-step done';

                // load transcript
                fetch(api_base_url + '/api/transcript/' + current_video_id_string).then(function(res2) {
                    if (res2.ok == true) {
                        res2.json().then(function(t_data) {
                            my_transcription_data = t_data;
                            
                            // build transcript
                            the_transcript_text_area.innerHTML = '';
                            for (var i = 0; i < my_transcription_data.segments.length; i++) {
                                var seg = my_transcription_data.segments[i];
                                
                                var span1 = document.createElement('span');
                                span1.className = 'timestamp';
                                span1.textContent = '[' + seg.start_formatted + ']';
                                span1.onclick = createJumpFunction(seg.start);
                                
                                var span2 = document.createElement('span');
                                span2.className = 'segment';
                                span2.textContent = ' ' + seg.text + ' ';
                                span2.onclick = createJumpFunction(seg.start);
                                
                                the_transcript_text_area.appendChild(span1);
                                the_transcript_text_area.appendChild(span2);
                            }
                            
                            // build objects
                            list_objects.innerHTML = '';
                            var obj_list = my_transcription_data.unique_objects;
                            if (obj_list == null || obj_list.length == 0) {
                                div_objects.classList.add('hidden');
                            } else {
                                div_objects.classList.remove('hidden');
                                for (var j = 0; j < obj_list.length; j++) {
                                    var o_name = obj_list[j];
                                    var tag_span = document.createElement('span');
                                    tag_span.className = 'object-tag';
                                    tag_span.textContent = o_name;
                                    tag_span.onclick = createSearchObjFunction(o_name);
                                    list_objects.appendChild(tag_span);
                                }
                            }
                        });
                    }
                });

                setTimeout(function() {
                    section_for_upload.classList.add('hidden');
                    section_for_search.classList.remove('hidden');
                    video_player_element.src = api_base_url + '/api/video/' + current_video_id_string;
                    video_player_element.load();
                    the_search_input.focus();
                }, 1000);
            });
        }
    }).catch(function(err) {
        console.error('Network error:', err);
        showToast('Upload failed. Is the server running?', 'error');
        the_progress_container.classList.add('hidden');
        upload_zone.style.display = '';
    });
}

function createJumpFunction(time_sec) {
    return function() {
        video_player_element.currentTime = time_sec;
        video_player_element.play();
        video_player_element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
}

function createSearchObjFunction(obj_text) {
    return function() {
        the_search_input.value = obj_text;
        performSearch();
    };
}

// search events
the_search_button.addEventListener('click', function() {
    performSearch();
});

the_search_input.addEventListener('keypress', function(event) {
    if (event.key == 'Enter') {
        performSearch();
    }
});

function performSearch() {
    var query_str = the_search_input.value.trim();
    if (query_str == '') {
        showToast('Type something to search for', 'error');
        the_search_input.focus();
        return;
    }

    if (current_video_id_string == null) {
        showToast('Please upload a video first', 'error');
        return;
    }

    the_search_button.disabled = true;
    the_search_button.innerHTML = '<div class="spinner"></div> Searching...';

    var my_body = {
        video_id: current_video_id_string,
        query: query_str
    };

    fetch(api_base_url + '/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(my_body)
    }).then(function(res) {
        if (res.ok == false) {
            res.json().then(function(err_data) {
                var msg = "Search failed";
                if (err_data.detail != null) {
                    msg = err_data.detail;
                }
                showToast(msg, 'error');
                
                the_search_button.disabled = false;
                var btn_html = '<span>Search</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
                the_search_button.innerHTML = btn_html;
            });
        } else {
            res.json().then(function(data) {
                div_no_results.classList.add('hidden');
                div_results.classList.add('hidden');
                list_results.innerHTML = '';

                if (data.result_count == 0) {
                    div_no_results.classList.remove('hidden');
                } else {
                    div_results.classList.remove('hidden');
                    title_results.textContent = 'Results for "' + query_str + '"';
                    count_results.textContent = data.result_count + ' found';

                    for (var k = 0; k < data.results.length; k++) {
                        var r = data.results[k];
                        var card_div = document.createElement('div');
                        card_div.className = 'result-card';
                        card_div.style.animationDelay = (k * 0.08) + 's';

                        var s_time = r.start_formatted;
                        if (r.precise_start_formatted != undefined) {
                            s_time = r.precise_start_formatted;
                        }

                        var j_time = r.start;
                        if (r.precise_start != undefined) {
                            j_time = r.precise_start;
                        }

                        var match_lbl = 'Exact Match';
                        var match_cls = 'exact';
                        
                        if (r.match_type == 'partial') {
                            match_lbl = 'Partial Match';
                            match_cls = 'partial';
                        }
                        if (r.match_type == 'object') {
                            match_lbl = 'Object Match';
                            match_cls = 'object';
                        }
                        if (r.match_type == 'description') {
                            match_lbl = 'Visual Match';
                            match_cls = 'description';
                        }

                        var regex = new RegExp('(' + escapeMyRegex(query_str) + ')', 'gi');
                        var hl_text = r.text.replace(regex, '<mark>$1</mark>');

                        var html_str = '';
                        html_str += '<div class="result-time">';
                        html_str += '  <div class="result-timestamp">' + s_time + '</div>';
                        html_str += '  <svg class="result-play-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">';
                        html_str += '    <polygon points="5 3 19 12 5 21 5 3"></polygon>';
                        html_str += '  </svg>';
                        html_str += '</div>';
                        html_str += '<div class="result-body">';
                        html_str += '  <div class="result-text">' + hl_text + '</div>';
                        html_str += '  <span class="result-match-type ' + match_cls + '">' + match_lbl + '</span>';
                        html_str += '</div>';
                        
                        card_div.innerHTML = html_str;
                        card_div.onclick = createJumpFunction(j_time);
                        list_results.appendChild(card_div);
                    }
                }
                
                the_search_button.disabled = false;
                var btn_html = '<span>Search</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
                the_search_button.innerHTML = btn_html;
            });
        }
    }).catch(function(err) {
        console.error('Search error:', err);
        showToast('Search failed', 'error');
        
        the_search_button.disabled = false;
        var btn_html = '<span>Search</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
        the_search_button.innerHTML = btn_html;
    });
}

function escapeMyRegex(my_str) {
    return my_str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// show or hide transcript
the_transcript_btn.addEventListener('click', function() {
    var has_open_class = false;
    if (the_transcript_btn.className.indexOf('open') > -1) {
        has_open_class = true;
    }
    
    if (has_open_class == false) {
        the_transcript_btn.classList.add('open');
        the_transcript_div.classList.remove('hidden');
        the_transcript_btn.querySelector('span').textContent = 'Hide Full Transcript';
    } else {
        the_transcript_btn.classList.remove('open');
        the_transcript_div.classList.add('hidden');
        the_transcript_btn.querySelector('span').textContent = 'Show Full Transcript';
    }
});

// start a new video
btn_new_video.addEventListener('click', function() {
    current_video_id_string = null;
    my_transcription_data = null;

    section_for_search.classList.add('hidden');
    section_for_upload.classList.remove('hidden');
    upload_zone.style.display = '';
    the_progress_container.classList.add('hidden');
    my_file_input.value = '';
    the_search_input.value = '';
    
    list_results.innerHTML = '';
    div_results.classList.add('hidden');
    div_no_results.classList.add('hidden');
    
    div_objects.classList.add('hidden');
    list_objects.innerHTML = '';
    
    the_transcript_div.classList.add('hidden');
    the_transcript_btn.classList.remove('open');
    the_transcript_btn.querySelector('span').textContent = 'Show Full Transcript';
    
    video_player_element.src = '';
    the_progress_fill_bar.style.width = '0%';
});
