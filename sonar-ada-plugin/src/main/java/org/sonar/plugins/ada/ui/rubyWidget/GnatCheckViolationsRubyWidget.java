/*
 * Sonar Ada Plugin
 * Copyright (C) 2012, AdaCore
 */
package org.sonar.plugins.ada.ui.rubyWidget;

import org.sonar.api.web.UserRole;
import org.sonar.api.web.AbstractRubyTemplate;
import org.sonar.api.web.Description;
import org.sonar.api.web.RubyRailsWidget;
import org.sonar.api.web.WidgetCategory;

@UserRole(UserRole.USER)
@Description("Shows Codepeer messages, per severity and category")
@WidgetCategory("Rules")
public class GnatCheckViolationsRubyWidget extends AbstractRubyTemplate implements RubyRailsWidget {

    public String getId() {
        return "GNATCheckViolations";
    }

    public String getTitle() {
        return "GNAT Check violations";
    }

    @Override
    protected String getTemplatePath() {
        return "/org/sonar/plugins/ada/ui/rubyWidget/gnatcheck_violations.html.erb";
    }
}
