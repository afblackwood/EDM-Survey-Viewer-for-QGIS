def classFactory(iface):

    from .edm_survey_viewer_plugin import EDMSurveyViewerPlugin

    return EDMSurveyViewerPlugin(iface)