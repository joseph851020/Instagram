/*
* Short library to create tooltips using Qtip. Takes data from html and creates
* the necessary tooltip.
* Requires:
*   - jQuery 1.9
*   - http://cdn.jsdelivr.net/qtip2/2.2.1/jquery.qtip.min.css 
*   - http://cdn.jsdelivr.net/qtip2/2.2.1/jquery.qtip.min.js
*
* Examples of HTML used:
<div class="hasTooltip" data-content="My content">?</div>
<div class="hasTooltip" data-content="My content" data-title="What is this?" 
					    data-position="at:top left;my:bottom center;">?</div>
<div class="hasTooltip" data-content="My content" data-title="What is this?" 
					    data-data-position-adjust-x="20">?</div>
*/
var ToolTip = function ($element) {
	/***
	* Creates a tooltip for the element passed by parameter
	* 
	***/
	var self = this;

	var content = $element.data("content");
	var title = $element.data("title");
	var position = $element.data("position");
	var position_adjust_x = $element.data("position-adjust-x");
	var position_adjust_y = $element.data("position-adjust-y");
    var styles = $element.data("styles");

	var options = { position: {}}
    if ('title' in $element.data() ){
    	options.content = { title: { text: title}, text: content}
    	if('button' in $element.data()){
    		options.content.button = $element.data("button");	
    	}
    }
    else{
    	options.content = {
            text: content,
        }
    }
    if (typeof position != "undefined"){
    	var pos = position.split(";");
    	options.position = { target: $element };
		for(var i=0; i< pos.length; i++){
			var s = pos[i].split(":");
			var attr = s[0];
			var val = s[1];
		    options.position[attr] = val;
		}
    }
    if (typeof position_adjust_x != "undefined"){
    	if (typeof options.position.adjust != "undefined"){
    		options.position.adjust.x = position_adjust_x
    	}
    	else{
    		options.position.adjust = { x: position_adjust_x};	
    	}
    	
    }
    if (typeof position_adjust_y != "undefined"){
        if (typeof options.position.adjust != "undefined"){
            options.position.adjust.y = position_adjust_y
        }
        else{
            options.position.adjust = { y: position_adjust_y};  
        }
        
    }
    if (typeof styles != "undefined"){
        options.style = {
            classes: styles,
        } 
    }
    $element.qtip(options);
}

$(document).ready(function(){
    $(".hasTooltip").each(function(){
        new ToolTip($(this));
    })
})