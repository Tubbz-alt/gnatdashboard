/**
 *
 * Sonar Ada Plugin
 */
package org.sonar.plugins.ada.utils;

import java.io.InputStream;
import java.util.List;
import org.sonar.api.rules.Rule;
import org.sonar.api.rules.RuleRepository;
import org.sonar.api.rules.XMLRuleParser;
import org.sonar.plugins.ada.Ada;

/**
 *
 * @author martin
 */
public abstract class AdaAbstractRuleRepository extends RuleRepository {

    protected abstract String fileName();

    public AdaAbstractRuleRepository(String key) {
        super(key, Ada.KEY);
    }

    @Override
    public List<Rule> createRules() {
        final XMLRuleParser xmlParser = new XMLRuleParser();
        final InputStream xmlStream = getClass().getResourceAsStream(fileName());
        return xmlParser.parse(xmlStream);

    }
}