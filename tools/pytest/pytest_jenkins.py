"""
Helper for pytest in jenkins.

To have a test output grouped by first 'package' then 'class' then
everything else, make the output xml have as testcase:

    <testcase classname="packagename.classame",
                   name="every.thing.else">

With only two elements in 'classname'.
This was found by trial and errors in the jenkins test output.
"""

import _pytest.junitxml


class JenkinsNodeReporter(_pytest.junitxml._NodeReporter):
    # pylint:disable=protected-access
    """_NodeReporter that changes classname to only keep 2 elements."""

    def record_testreport(self, testreport):
        """Update the classname and name to be processed as wanted by jenkins.

        It is done after the original 'record_testreport' that handles
        command line arguments.

        'classname' is restricted to its only 2 first parts.
        'name' attribute gets the rest of classname and name concatenated
        """

        super().record_testreport(testreport)

        # Value of 'name' is stored in "attrs['name'].uniobj" as it is an
        # 'xml.raw' which does not need to be re-converted later.
        name = self.attrs['name'].uniobj
        # Expect 'classname' to not need conversion
        classname = self.attrs['classname']

        classnames = classname.split('.')

        # This function is currently called two times, so ignore the second one
        # If classname is smaller than 2, ignore as not sure how to handle
        # splitting the test name.
        if len(classnames) <= 2:
            return

        names = classnames[2:] + [name]
        self.attrs['name'].uniobj = '.'.join(names)
        self.attrs['classname'] = '.'.join(classnames[0:2])

    @classmethod
    def items_use_reporter(cls, config, items):
        """Add a current reporter to 'config._xml' as done in junitxml.py."""
        try:
            config_xml = getattr(config, "_xml")
            for item in items:
                cls._item_use_reporter(config_xml, item)
        except AttributeError:
            pass

    @classmethod
    def _item_use_reporter(cls, config_xml, item):
        reporter = cls(item.nodeid, config_xml)
        key = (item.nodeid, getattr(item, 'node', None))
        config_xml.node_reporters[key] = reporter
        config_xml.node_reporters_ordered.append(reporter)


def pytest_collection_modifyitems(config, items):
    """Replace nodes reporter to use 'JenkinsNodeReporter'.

    This will allow modifying testcases classname and name.
    """
    JenkinsNodeReporter.items_use_reporter(config, items)
