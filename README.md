# Why Visual Testing

Functional tests are great for checking known inputs against their desired outputs, but it’s nearly impossible to assert visual “correctness” with code.

As we are not actually testing anything visually, and there are so many things that can make your tests “pass” while resulting in a visual regression. Class attributes can change, other overriding classes can be applied, etc. It’s also hard to account for visual bugs caused by how elements get rendered by different browsers and devices.

When browsers and devices are part of the equation, it becomes even harder to assert the desired outcomes in tests. Trying to assert all those edge cases only exacerbates the challenge above and doesn’t give you a way to test new visual elements that come along.

# About Utility

This Visual testing tool has been created based on openCV and Pillow which takes baseline snapshot through visual tests across the pages and saves for future references. During actual execution scnapshots of specific pages are taken and compared with baseline screenshots and perform pixel to pixel comparison

This tool is created with the combination of selenium, python and behave and tool actually get few parameters from tests with the help for these tools.