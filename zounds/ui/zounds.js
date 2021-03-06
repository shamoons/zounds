$(function() {

    var events = {
        FEATURE_RECEIVED: 'FEATURE_RECEIVED',
        PLAY: 'PLAY',
        NEXT: 'NEXT',
        PREVIOUS: 'PREVIOUS'
    };

    function MessageBus() {

        this.publish = function(event, data) {
            $(document).trigger(event, data);
        }

        this.subscribe = function(event, func) {
            $(document).on(event, func);
        }

        this.unsubscribe = function(events) {
            $(document).off(events.join(' '));
        }

    }

    function PngImage(url, root) {
        $('<img>').attr('src', url).appendTo(root);
    }

    function BasicAudio(url, root, bus) {
        var
            self = this,
            audio = $('<audio>').attr('controls', true);
        $('<source>').attr('src', url).appendTo(audio);
        audio.appendTo(root);

        this.isPlaying = function() {
            var el = audio[0];
            return el.duration > 0 && !el.paused;
        }

        bus.subscribe(events.PLAY, function(event, data) {
            if(self.isPlaying()) {
                audio[0].pause();
            } else {
                audio[0].play();
            }
        });

        this.destroy = function() {
            bus.unsubscribe([events.PLAY]);
        }
    }

    function SearchResults(data, root, context, client, bus) {
        var
            position = 0,
            container = $('<div>'),
            el = $('<div>'),
            self = this;

        this.render = function() {
            container.empty();
            self.slice = new AudioSlice(
                data[position], container, context, client, bus);
        }

        this.next = function() {
            position += 1;
            if(position >= data.length){
                position = 0;
            }
            self.render();
        }

        this.previous = function() {
            position -= 1;
            if(position < 0) {
                position = data.length - 1;
            }
            self.render();
        }

        this.play = function() {
            self.slice.play();
        }

        el.append(container);
        root.append(el);
        self.render();

        bus.subscribe(events.PLAY, self.play);

        bus.subscribe(events.PREVIOUS, self.previous);

        bus.subscribe(events.NEXT, self.next);

        this.destroy = function() {
            bus.unsubscribe([events.PLAY, events.PREVIOUS, events.NEXT]);
        }
    }

    function Visualization(selector, bus, context, client) {
        var
            self = this,
            el = $(selector);

        bus.subscribe(events.FEATURE_RECEIVED, function(event, data) {

            el.empty();
            if(self.view && self.view.destroy) {
                self.view.destroy();
            }

            if(data.contentType === 'image/png') {
                self.view = new PngImage(data.url, el);
                return;
            }

            if(data.contentType === 'audio/ogg') {
                self.view = new BasicAudio(data.url, el, bus);
                return;
            }

            if(data.contentType == 'application/vnd.zounds.searchresults+json'
                || data.contentType == 'application/vnd.zounds.onsets+json') {
                $.ajax({
                    method: 'GET',
                    url: data.url,
                    dataType: 'json'
                }).done(function(resp) {
                    console.log(resp);
                    self.view = new SearchResults(
                        resp.results, el, context, client, bus);
                });
            }
        });

        el.keydown(function(e) {
            if(e.which === 32) {
                bus.publish(events.PLAY);
            } else if(e.which === 37) {
                bus.publish(events.PREVIOUS);
            } else if(e.which === 39) {
                bus.publish(events.NEXT);
            }
        });

    }

    function History() {

        var history = [];

        this.push = function(item) {
            if(!item || item === '') { return; }
            history.push(item);
        }

        this.fetch = function(index) {
            var value = history[history.length - index];
            return value;
        }

        this.count = function() {
            return history.length;
        }
    }

    function Console(inputSelector, outputSelector, messageBus, client) {
        var
            input = $(inputSelector),
            output = $(outputSelector),
            history = new History(),
            history_pos = 0;

        function fetch() {
            value = history.fetch(history_pos);
            input.val(value);
            if(!value) { return; }
            setTimeout(function() {
                input.get(0).setSelectionRange(value.length, value.length);
            }, 0);
        }

        $(document).keydown(function(e) {
            if(e.which === 38 && history_pos < history.count()) {
                history_pos += 1;
                fetch();
                return;
            }

            if(e.which === 40 && history_pos > 0) {
                history_pos -= 1;
                fetch();
                return;
            }
        });

        input.keypress(function(e) {
            var command = $(this).val();

            if(e.which === 13) {
                client
                    .interpret(command)
                    .always(function(data) {
                        history.push(command);
                        history_pos = 0;
                        output.append($('<div>').addClass('statement').text(command));
                    })
                    .done(function(data) {
                        if(data.url && data.contentType) {
                            messageBus.publish(events.FEATURE_RECEIVED, data);
                        }
                        output.append($('<div>').addClass('result').text(data.result));
                        window.scrollTo(0,document.body.scrollHeight);
                    })
                    .fail(function(data) {
                        output.append($('<div>').addClass('error').text(data.responseJSON.error));
                        window.scrollTo(0 ,document.body.scrollHeight);
                    });
                $(this).val('');
            }
        });
    }

    var client = new ZoundsClient({
        interpret: function(command) {
            return {
                method: 'POST',
                url: '/zounds/repl',
                data: command,
                dataType: 'json',
                contentType: 'text/plain'
            };
        }
    });

    var audioContext = new AudioContext();
    var bus = new MessageBus();
    var input = new Console('#input', '#output', bus, client);
    var vis = new Visualization('#visualization', bus, audioContext, client);
});