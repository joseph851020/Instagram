
'use strict';

module.exports = function(grunt) {

  // Load grunt tasks automatically
  require('load-grunt-tasks')(grunt);

  // Time how long tasks take. Can help when optimizing build times
  require('time-grunt')(grunt);

  // Configurable paths for the application
  var app = require('./package.json');
  var appConfig = {
    name: app.name,
    banner: '/*!\n' +
      ' * Quirk UI v'+ app.version +' ('+ app.homepage +')\n' +
      ' * Copyright 2015 '+ app.author +'\n' +
      ' *\n' +
      ' * Last compiled on <%= grunt.template.today("dddd, mmmm dS, yyyy, h:MM:ss TT") %>\n' +
      ' */\n'
  };

  // Define the configuration for all the tasks
  grunt.initConfig({

    // Project settings
    pkg: appConfig,

    watch: {
      bower: {
        files: ['bower.json'],
        tasks: ['build']
      },
      less: {
        files: ['less/*.less'],
        tasks: ['less', 'usebanner']
      },
      html: {
        files: ['templates/{,*/}*.html'],
        options: {
          livereload: '<%= connect.options.livereload %>'
        }
      },
      css: {
        files: ['css/{,*/}*.css'],
        options: {
          livereload: '<%= connect.options.livereload %>'
        }
      },
      documentation: {
        files: ['documentation/index.html'],
        options: {
          livereload: '<%= connect.options.livereload %>'
        }
      }
    },

    // The actual grunt server settings
    connect: {
      options: {
        port: 9000,
        open: true,
        livereload: 35729,
        // Change this to '0.0.0.0' to access the server from outside
        hostname: '0.0.0.0'
      },
      templates: {
        options: {
          open: true,
          middleware: function (connect) {
            return [
            connect().use('/bower_components', connect.static('./bower_components')),
            connect().use('/lib', connect.static('./lib')),
            connect().use('/images', connect.static('./images')),
            connect().use('/css', connect.static('./css')),
            connect().use('/fonts', connect.static('./fonts')),
            connect().use('/js', connect.static('./js')),
            connect.static('templates'),
            ];
          }
        }
      },
      documentation: {
        options: {
          open: true,
          middleware: function (connect) {
            return [
            connect().use('/lib', connect.static('./lib')),
            connect().use('/images', connect.static('./images')),
            connect().use('/css', connect.static('./css')),
            connect().use('/fonts', connect.static('./fonts')),
            connect().use('/js', connect.static('./js')),
            connect.static('documentation'),
            ];
          }
        }
      }
    },

    // Compiles less files to css
    less: {
      dist: {
        files: {
          'css/<%= pkg.name %>.css' : 'less/<%= pkg.name %>.less'
        }
      }
    },

    // Adds banner to files
    usebanner: {
      dist: {
        files: {
          src: ['css/*.css']
        },
        options: {
          position: 'top',
          banner: '<%= pkg.banner %> <%= pkg.bootstrapBanner %>'
        }
      }
    },

    // Make sure code styles are up to par and there are no obvious mistakes
    jshint: {
      options: {
        jshintrc: '.jshintrc',
        reporter: require('jshint-stylish')
      },
      all: {
        src: [
        'Gruntfile.js',
        'templates/**/*.js'
        ]
      }
    },

    bower: {
      install: {
        options: {
          cleanTargetDir: true,
          layout: 'byComponent'
        }
      }
    }
  });

  grunt.registerTask('default', [
    'less',
    'usebanner',
    'connect:templates',
    'watch'
  ]);

  grunt.registerTask('docs', [
    'connect:documentation',
    'watch:documentation'
  ]);

  grunt.registerTask('build', ['bower']);

};
