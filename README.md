# Firebase Quickstarts for Android

A collection of quickstart samples demonstrating the Firebase APIs on Android. For more information, see https://firebase.google.com.

## Samples

You can open each of the following samples as an Android Studio project, and run
them on a mobile device or a virtual device (AVD). When doing so you need to
add each sample app you wish to try to a Firebase project on the [Firebase
console](https://console.firebase.google.com). You can add multiple sample apps
to the same Firebase project. There's no need to create separate projects for
each app.

To add a sample app to a Firebase project, use the `applicationId` value specified
in the `app/build.gradle` file of the app as the Android package name. Download
the generated `google-services.json` file, and copy it to the `app/` directory of
the sample you wish to run.

- [Admob](admob/README.md)
- [Analytics](analytics/README.md)
- [App-Indexing](app-indexing/README.md)
- [Auth](auth/README.md)
- [Config](config/README.md)
- [Crash](crash/README.md)
- [Database](database/README.md)
- [Firestore](firestore/README.md)
- [Functions](functions/README.md)
- [Dynamic Links](dynamiclinks/README.md)
- [In-App Messaging](inappmessaging/README.md)
- [Messaging](messaging/README.md)
- [ML Kit](mlkit/README.md)
- [ML Kit LanguageID](mlkit-langid/README.md)
- [ML Kit Smart Reply](mlkit-smartreply/README.md)
- [ML Kit Translate](mlkit-translate/README.md)
- [Performance Monitoring](perf/README.md)
- [Storage](storage/README.md)

## Project Management

A Python-based project management system is available to help manage the Firebase quickstart modules:

```bash
# List all modules
python project_management_system.py list

# Setup all modules with mock google-services.json
python project_management_system.py setup-all

# Setup a specific module
python project_management_system.py setup --module auth

# Build a specific module
python project_management_system.py build --module analytics

# Run tests for a module
python project_management_system.py test --module database

# Display project information
python project_management_system.py info
```

For more commands and usage, run:
```bash
python project_management_system.py --help
```

## How to make contributions?
Please read and follow the steps in the [CONTRIBUTING.md](CONTRIBUTING.md)

[![Actions Status][gh-actions-badge]][gh-actions]

[gh-actions]: https://github.com/firebase/quickstart-android/actions
[gh-actions-badge]: https://github.com/firebase/quickstart-android/workflows/Android%20CI/badge.svg
