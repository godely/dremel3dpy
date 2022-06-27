Changelog
-----------

A list of changes between each release.

2.0.0 (2022-06-27)
- Remove streaming functionality, which depended on tkinter library.

1.1.1 (2022-06-26)
- Just upgrade version for testing purposes

1.1.0 (2022-06-26)
- Add get_job_name function that strips out the .gcode extension from the name
- Rename manufacturer to Dremel
- Add default values for original and scale attributes on get_snapshot_as_ndarray

1.0.1 (2022-06-20)
- Remove OpenCV-Python dependency from setup.py

1.0.0 (2022-06-20)
- Remove OpenCV-Python dependency

0.5.6 (2022-06-18)
- Remove tuple type from API return types

0.5.5 (2022-06-18)
- Change dict to Dict in API return types

0.5.4 (2022-06-18)
- Loosen requirements versioning [2]

0.5.3 (2022-06-18)
- Loosen requirements versioning

0.5.2 (2022-06-18)
- Fix requirements

0.5.1 (2022-06-18)
- Adjust versioning of dependencies to be >=

0.5.0 (2022-06-18)
- Add CLI and remove versioning from dependencies

0.4.0 (2022-05-21)
^^^^^^^^^^^^^^^^^^
- Add camera timelapse functionality

0.3.4 (2022-05-20)
^^^^^^^^^^^^^^^^^^
- Added back requirements.txt

0.3.3 (2022-05-20)
^^^^^^^^^^^^^^^^^^
- Added return statement to boolean methods and fixed firmware version return

0.3.2 (2022-05-20)
^^^^^^^^^^^^^^^^^^
- Minor fixes

0.3.1 (2022-05-20)
^^^^^^^^^^^^^^^^^^
- Added is_door_open method to the API

0.3.0 (2022-05-20)
^^^^^^^^^^^^^^^^^^
- Added several new methods to the API

0.2.0 (2022-05-19)
^^^^^^^^^^^^^^^^^^
- Added several new methods to the API

0.1.0 (2022-05-19)
^^^^^^^^^^^^^^^^^^
- Added several new methods to the API

0.0.2 (2022-05-19)
^^^^^^^^^^^^^^^^^^
- Update .gitignore to remove unnecessary files

0.0.1 (2022-05-18)
^^^^^^^^^^^^^^^^^^
- Initial release of dremel3dpy